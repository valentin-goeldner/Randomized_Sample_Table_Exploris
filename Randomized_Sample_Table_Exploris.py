import csv
import random
import os


def create_lc_hrms_sample_table(input_csv_path, output_csv_path,
    randomize=True):
  """
      Generates an LC-HRMS sample table with interleaved blanks and QCs.

      Args:
          input_csv_path (str): Path to the input CSV file.
          output_csv_path (str): Path where the generated CSV table will be saved.
          randomize (bool): If True, shuffles the unknown samples. If False, keeps original order.
  """
  try:
    with open(input_csv_path, 'r', newline='', encoding='utf-8') as infile:
      reader = csv.reader(infile)

      # Read metadata
      metadata_list = []
      for row in reader:
        if not row or not row[0].strip():
          break
        metadata_list.append(row)
      metadata = {row[0].strip(): row[1].strip() for row in metadata_list if
                  len(row) > 1}

      # Read headers and sample data
      try:
        sample_data_headers = next(reader)
      except StopIteration:
        raise ValueError("No sample data headers found after metadata.")

      required_data_cols = {"Sample Type", "Sample ID", "Position"}
      if not required_data_cols.issubset(set(sample_data_headers)):
        raise ValueError(
            f"Input data section missing required columns: {', '.join(required_data_cols)}."
        )

      samples = {
        "Blank": [],
        "QC": [],
        "Equilibration": [],
        "SSM": [],
        "Unknown": []
      }
      for row_data in reader:
        if not row_data or not row_data[0].strip():
          continue
        row_dict = dict(zip(sample_data_headers, row_data))
        sample_type = row_dict.get("Sample Type", "").strip()
        if sample_type in samples:
          samples[sample_type].append(row_dict)
        else:
          samples["Unknown"].append(row_dict)

  except (FileNotFoundError, ValueError) as e:
    print(f"Error reading input file: {e}")
    return

  # Detect and verify sample types
  print("\n--- Detected Sample Types ---")
  for stype in ["Blank", "QC", "Equilibration", "SSM"]:
    status = f"PRESENT ({len(samples[stype])} samples)" if samples[
      stype] else "ABSENT"
    print(f"  {stype:15}: {status}")

  verify = input(
    "\nDo you verify and want to proceed with these detected types? (y/n) [default: y]: ").strip().lower()
  if verify == 'n':
    print("Execution halted by user.")
    return

  # Extract available templates
  if not samples["Blank"]:
    print("Error: Input CSV must contain at least one 'Blank' sample.")
    return

  instrument_blank_template = samples["Blank"][0]
  ssm_templates = samples["SSM"]  # Can be empty
  qc_templates = samples["QC"]  # Can be empty

  # Equilibration template is optional
  equilibration_template = samples["Equilibration"][0] if samples[
    "Equilibration"] else None
  unknown_samples = samples["Unknown"]

  # Validate and parse metadata
  required_meta = {"Polarity", "Path", "Instrument Method", "Injection volume",
                   "Date of analysis", "Initials"}
  if not required_meta.issubset(set(metadata.keys())):
    print(
        f"Error: Missing required metadata keys: {', '.join(required_meta.difference(metadata.keys()))}.")
    return

  try:
    metadata["Technical replicates"] = int(
      metadata.get("Technical replicates", 1))
    metadata["Max QC distance"] = int(metadata.get("Max QC distance", 10))
    metadata["Equilibration"] = int(
      metadata.get("Equilibration", 5)) if equilibration_template else 0
    # Parse Leading Blanks (defaults to 1 if not present in the input file)
    metadata["Leading blanks"] = int(metadata.get("Leading blanks", 1))
  except ValueError:
    print(
        "Error: Technical replicates, Max QC distance, Equilibration, and Leading blanks must be integers.")
    return

  # Generate technical replicates
  replicated_unknowns = [
    sample.copy() for sample in unknown_samples
    for _ in range(metadata["Technical replicates"])
  ]

  if randomize:
    print("Randomizing sample run order...")
    random.shuffle(replicated_unknowns)
  else:
    print("Maintaining original sample run order.")

  # Prepare output structure and helper functions
  final_sequence = []
  injection_counter = 1
  sample_specific_counts = {}
  output_headers = [
    "Sample Type", "File Name", "Sample ID", "Path", "Instrument Method",
    "Calibration File", "Position", "Inj Vol", "Level", "Sample Wt",
    "Sample Vol", "ISTD Amt", "Dil Factor", "L1 Study", "L2 Client",
    "L3 Laboratory", "L4 Company", "L5 Phone", "Comment", "Sample Name"
  ]

  def add_injection(template_row):
    nonlocal injection_counter
    new_row = {header: '' for header in output_headers}
    new_row.update(template_row)

    # Map Sample Type output to only allow Blank, QC, or Unknown
    orig_type = template_row.get("Sample Type", "Unknown").strip()
    if orig_type in ["Equilibration", "SSM", "Unknown", ""]:
      new_row["Sample Type"] = "Unknown"
    else:
      new_row["Sample Type"] = orig_type  # Will remain "Blank" or "QC"

    new_row["Path"] = metadata["Path"]
    new_row["Instrument Method"] = metadata["Instrument Method"]
    new_row["Inj Vol"] = metadata["Injection volume"]
    new_row["Sample Name"] = new_row["Sample ID"]

    sample_id = new_row["Sample ID"]
    sample_specific_counts[sample_id] = sample_specific_counts.get(sample_id,
                                                                   0) + 1

    file_name = (
      f"{metadata['Date of analysis']}_{metadata['Initials']}_{injection_counter:03d}_"
      f"{sample_id}_{metadata.get('Polarity', '').lower()}_{sample_specific_counts[sample_id]:02d}"
    )
    new_row["File Name"] = file_name

    final_sequence.append(new_row)
    injection_counter += 1

  def add_qc_block():
    # Only add QCs if they actually exist in the templates
    if qc_templates:
      for qc_temp in qc_templates:
        add_injection(qc_temp)
    add_injection(instrument_blank_template)

  # --- Assemble final sequence ---

  # 1. Leading Blanks
  for _ in range(metadata["Leading blanks"]):
    add_injection(instrument_blank_template)

  # 2. Equilibration & Reference Blank
  # We only add the post-equilibration Reference Blank if equilibration was actually run
  if equilibration_template and metadata["Equilibration"] > 0:
    for _ in range(metadata["Equilibration"]):
      add_injection(equilibration_template)
    # Reference Blank to clean system after equilibration
    add_injection(instrument_blank_template)

  # 3. Standard Reference Material / SSM
  if ssm_templates:
    for ssm_temp in ssm_templates:
      add_injection(ssm_temp)

  # 4. QC Block (if QCs exist)
  if qc_templates:
    add_qc_block()

  # 5. Unknowns Sequence
  unknown_count_in_block = 0
  for sample_row in replicated_unknowns:
    add_injection(sample_row)
    unknown_count_in_block += 1
    if unknown_count_in_block % metadata["Max QC distance"] == 0:
      add_qc_block()
      unknown_count_in_block = 0

  # 6. Post-sequence / Bracket Close
  if unknown_count_in_block > 0:
    add_injection(instrument_blank_template)
    if ssm_templates:
      for ssm_temp in ssm_templates:
        add_injection(ssm_temp)
    if qc_templates:
      add_qc_block()
  else:
    if ssm_templates:
      for ssm_temp in ssm_templates:
        add_injection(ssm_temp)
    add_injection(instrument_blank_template)

  # Write output CSV
  try:
    with open(output_csv_path, 'w', newline='', encoding='utf-8') as outfile:
      writer = csv.writer(outfile)
      writer.writerow(["Bracket Type=4,"])
      writer.writerow(output_headers)
      writer.writerows(
          (row_dict.get(h, '') for h in output_headers) for row_dict in
          final_sequence)

    print(f"Successfully generated sample table to '{output_csv_path}'.")
    print(f"Total injections in sequence: {len(final_sequence)}")
  except Exception as e:
    print(f"Error writing output CSV: {e}")


if __name__ == "__main__":
  input_file = input("Enter the path to your input CSV file: ").strip().strip(
    '\"')
  base, ext = os.path.splitext(input_file)
  default_output_file = f"{base}_sequence{ext}"
  output_file = input(
      f"Enter the path for the output CSV file (default: {default_output_file}): ").strip() or default_output_file

  randomize_choice = input(
    "Do you want to randomize the sample order? (y/n) [default: y]: ").strip().lower()
  do_randomize = randomize_choice != 'n'

  if os.path.exists(input_file):
    create_lc_hrms_sample_table(input_file, output_file, randomize=do_randomize)
  else:
    print(f"Error: The provided input file path does not exist: '{input_file}'")