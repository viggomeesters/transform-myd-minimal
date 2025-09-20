#!/usr/bin/env python3
"""Create test XML files for testing F02 error scenarios."""

from pathlib import Path

# Create test directory
test_dir = Path("data/02_target")
test_dir.mkdir(parents=True, exist_ok=True)

# Create a valid XML file with target fields for a specific variant
valid_xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<Workbook xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
    <ss:Worksheet ss:Name="Field List">
        <ss:Table>
            <ss:Row>
                <ss:Cell ss:Index="2"><ss:Data ss:Type="String">Sheet Name</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">Group Name</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">Field Description</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">Importance</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">Type</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">Length</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">Decimal</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">SAP Structure</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">SAP Field</ss:Data></ss:Cell>
            </ss:Row>
            <ss:Row>
                <ss:Cell ss:Index="2"><ss:Data ss:Type="String">TestSheet</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">main</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">Test Field 1</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">mandatory</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">CHAR</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">10</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">0</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">S_VALID</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">test_field_1</ss:Data></ss:Cell>
            </ss:Row>
            <ss:Row>
                <ss:Cell ss:Index="2"><ss:Data ss:Type="String">TestSheet</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">key</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">Test Field 2</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">mandatory</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">NUMC</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">5</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">0</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">S_VALID</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">test_field_2</ss:Data></ss:Cell>
            </ss:Row>
        </ss:Table>
    </ss:Worksheet>
</Workbook>'''

# Create valid XML file with structure S_VALID
valid_file = test_dir / "index_target_valid_valid.xml"
with open(valid_file, "w", encoding="utf-8") as f:
    f.write(valid_xml_content)
print(f"Created valid XML test file: {valid_file}")

# Create XML file without matching structure (no S_NOMATCH)
no_match_xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<Workbook xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
    <ss:Worksheet ss:Name="Field List">
        <ss:Table>
            <ss:Row>
                <ss:Cell ss:Index="2"><ss:Data ss:Type="String">Sheet Name</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">Group Name</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">Field Description</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">Importance</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">Type</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">Length</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">Decimal</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">SAP Structure</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">SAP Field</ss:Data></ss:Cell>
            </ss:Row>
            <ss:Row>
                <ss:Cell ss:Index="2"><ss:Data ss:Type="String">TestSheet</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">main</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">Other Field</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">mandatory</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">CHAR</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">10</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">0</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">S_OTHER</ss:Data></ss:Cell>
                <ss:Cell><ss:Data ss:Type="String">other_field</ss:Data></ss:Cell>
            </ss:Row>
        </ss:Table>
    </ss:Worksheet>
</Workbook>'''

# Create XML file that will not match the target variant
no_match_file = test_dir / "index_target_nomatch_nomatch.xml"
with open(no_match_file, "w", encoding="utf-8") as f:
    f.write(no_match_xml_content)
print(f"Created no-match XML test file: {no_match_file}")

# Create XML file without Field List worksheet
no_worksheet_xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
<Workbook xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
    <ss:Worksheet ss:Name="Other Sheet">
        <ss:Table>
            <ss:Row>
                <ss:Cell><ss:Data ss:Type="String">Some Data</ss:Data></ss:Cell>
            </ss:Row>
        </ss:Table>
    </ss:Worksheet>
</Workbook>'''

# Create XML file that will trigger worksheet not found error
no_worksheet_file = test_dir / "index_target_noworksheet_test.xml"
with open(no_worksheet_file, "w", encoding="utf-8") as f:
    f.write(no_worksheet_xml_content)
print(f"Created no-worksheet XML test file: {no_worksheet_file}")

print("Test XML files created successfully!")