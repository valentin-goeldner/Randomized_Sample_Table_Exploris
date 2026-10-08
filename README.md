When preparing your input sequence spreadsheet, please adhere to the following to ensure the script processes your sequence successfully:

1. Metadata Block (Rows 1 to 10)

Do not leave any empty lines in this section.
Ensure all the following exact keys are present in the first column:
Polarity: (e.g., pos or neg)
Path: The instrument directory path where data files will be stored.
Instrument Method: The method name on the instrument PC.
Injection volume: Integer representing µL injected.
Date of analysis: Format as YYYYMMDD (used in generated file names).
Initials: Your 2 or 3 letter initials.
Technical replicates: Integer for the number of times each Unknown sample is injected.
Max QC/blank distance: Integer representing how many Unknown injections can run before a QC block or Blank is injected.
Equilibration: Integer representing the number of conditioning injections.
Leading blanks: Integer representing how many pure blank injections start the run.

2. The Separator (Row 11)

Keep exactly one entirely blank row separating the metadata from the sample data.

3. Sample Data Block (Row 12 onwards)

The headers must include: Sample Type, Sample ID, and Position.
Accepted Sample Types are:
Blank (Required: At least 1 template row)
QC (Optional: Multi-injection Quality Control)
Equilibration (Optional: System conditioning)
SSM (Optional: System Suitability Mixture)
Unknown (Your study samples)
Position Format Rules:
Position names are case-sensitive and must strictly match this pattern: [Tray]:[Row][Column]
Tray can only be: R, G, B, or Y
Row can only be: A, B, C, D, E, or F
Column can only be a number from: 1 to 9
Example correct positions: R:A1, G:F9, Y:B3, B:C5
Avoid Duplicates: Do not assign the same physical position to different Sample IDs unless intended.
