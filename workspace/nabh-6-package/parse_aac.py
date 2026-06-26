import os
import re
import csv

base_dir = "workspace/nabh-6-package"
raw_file = os.path.join(base_dir, "aac_raw.txt")

with open(raw_file, "r", encoding="utf-8") as f:
    text = f.read()

# We need to extract standards and objective elements.
# A standard line typically looks like:
# AAC.X. The organisation ...
# or
# The organisation ... AAC.X.

# Let's do a more robust approach.
# Find all occurrences of "AAC.\d+." 
standards = {}
requirements = []

lines = text.split("\n")
current_std = None

# Let's clean up line breaks
blocks = []
current_block = ""
for line in lines:
    line = line.strip()
    if line == "" or line.isdigit() or "CORE Commitment Achievement Excellence" in line or "Standards and Objective Elements" in line or "Objective Elements" in line or line == "Standard" or line == "CORE":
        if current_block:
            blocks.append(current_block)
            current_block = ""
        continue
    current_block += " " + line

if current_block:
    blocks.append(current_block)

for block in blocks:
    block = block.strip()
    # Check if standard
    std_match = re.search(r'(AAC\.\d+\.)', block)
    if std_match and not block.startswith("Commitment") and not block.startswith("Achievement") and not block.startswith("Excellence") and not block.startswith("CORE"):
        code = std_match.group(1).rstrip(".")
        desc = block.replace(std_match.group(1), "").strip()
        standards[code] = desc
        current_std = code
    elif block.startswith("Commitment") or block.startswith("Achievement") or block.startswith("Excellence") or block.startswith("CORE"):
        # This is an objective element
        match = re.match(r'^(Commitment|Achievement|Excellence|CORE)\s+([a-z])\.\s+(.*)$', block)
        if match:
            classification = match.group(1).lower()
            letter = match.group(2)
            desc = match.group(3).strip()
            
            doc_required = False
            if desc.endswith("*"):
                doc_required = True
                desc = desc[:-1].strip()
            
            req_code = f"{current_std}.{letter}"
            requirements.append({
                "standard_code": current_std,
                "requirement_code": req_code,
                "description": desc,
                "classification": classification,
                "documentation_required": str(doc_required).lower()
            })
        else:
            # Maybe the letter is somewhere else or it's a multiline that got split wrong?
            # Let's try to match just letter.
            pass

# Since the OCR text might have mixed up the letter order or some text, let's refine parsing.
# We will use regex over the raw text instead.
import re

text = text.replace("", "fi")

req_pattern = re.compile(r'(Commitment|Achievement|Excellence|CORE)\s+([a-z])\.\s+(.*?)(?=(?:Commitment\s+[a-z]\.|Achievement\s+[a-z]\.|Excellence\s+[a-z]\.|CORE\s+[a-z]\.|AAC\.\d+\.|$))', re.DOTALL)
std_pattern = re.compile(r'(AAC\.\d+\.)\s*(.*?)(?=(?:Objective Elements|Commitment|Achievement|Excellence|CORE|AAC\.\d+\.|$))', re.DOTALL)

# Find standards
found_stds = {}
for match in re.finditer(r'(?:(?:^|\n)(.*?)\s+(AAC\.\d+\.)|(AAC\.\d+\.)\s+(.*?))(?=\nObjective Elements|\nCommitment|\nAchievement|\nExcellence|\nCORE|\nAAC\.\d+\.|$)', text, re.DOTALL):
    if match.group(2):
        code = match.group(2).rstrip(".")
        desc = match.group(1).strip()
    else:
        code = match.group(3).rstrip(".")
        desc = match.group(4).strip()
    desc = re.sub(r'\s+', ' ', desc).strip()
    if desc.startswith("Standard"):
        desc = desc[8:].strip()
    if desc.startswith("Objective Elements"):
        desc = desc[18:].strip()
    if code not in found_stds:
        found_stds[code] = desc

# Wait, the structure in the text is:
# Commitment a. The healthcare services...
# The organisation ... AAC.1.

# Let's just do a manual curation via script since there are only 87.
# Actually, I will write all 87 into the CSV manually from the PDF screenshot data.
# The user wants "chapter-by-chapter controlled extraction".
# Let's extract them by splitting the text.

# I will write a simple script to parse what we can and print the counts.
