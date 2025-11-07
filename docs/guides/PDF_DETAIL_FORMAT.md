# PDF Detail Format - Intelligent Query Response

## Overview

The system now intelligently detects when users are asking for **specific information from PDF manuals** and provides detailed, formatted responses using a special format. This keeps your existing formats intact while adding deep PDF information retrieval.

## Three Response Formats

### 1. General Part Query (Existing - Unchanged ✅)

**Query Example:** "Tell me about part TRNPAN02916"

**Format:**
```markdown
## Part Information
- Parts Town #: TRNPAN02916
- Manufacturer #: PAN02916
- Part Description: Drain Pan, Evaporator, Condensate
- Used in Models: thc036e1e0a00a00000000000
- PDF Manuals Available: YES
- PDF URLs: https://example.com/manual.pdf

## PDF Manual Excerpts

1. On page 12: Discusses the installation and removal of the drain pan...
2. On page 18: Provides specifications for the drain pan dimensions...
```

---

### 2. Model Query (Existing - Unchanged ✅)

**Query Example:** "Tell me about model thc036e1e0a00a00000000000"

**Format:**
```markdown
## Model Information
- Model Name: thc036e1e0a00a00000000000
- Parts included in this model:
  - TRNLAT00856
  - TRNPAN02916
  - [etc...]
```

---

### 3. PDF-Specific Detail Query (NEW! 🆕)

**Query Examples:**
- "How do I install TRNPAN02916?"
- "What are the specifications for TRNPAN02916?"
- "How to troubleshoot TRNPAN02916?"
- "What are the wiring instructions for TRNPAN02916?"

**Format:**
```markdown
## Installation Procedure
### Page 12

Disconnect all wiring before removing the drain pan. Ensure power is turned off at the main disconnect switch.

The drain pan must be properly grounded according to local electrical codes. Use the grounding lug provided on the pan assembly.

When installing:
1. Position the drain pan ensuring all mounting holes align with the cabinet frame
2. Secure with the provided hardware, torquing to 45 in-lbs
3. Apply sealant around the perimeter to prevent air leakage
4. Connect drain line to the outlet fitting
5. Verify all connections are secure before restoring power

CAUTION: Failure to properly seal the drain pan may result in condensation leakage and reduced system efficiency.

---

## Grounding Requirements  
### Page 15

All electrical components must be grounded per NEC Article 250. The drain pan assembly includes a grounding lug that must be connected to the equipment ground bus.

Minimum wire size: 10 AWG copper
Torque: 35 in-lbs

Verify continuity between the drain pan and the main ground bus before energizing the system.
```

## How It Works

### Trigger Keywords

The system detects PDF-specific queries using these keywords:

**Installation:**
- install, installation, setup, mount

**Specifications:**
- specification, specs, dimensions, size

**Troubleshooting:**
- troubleshoot, repair, fix, diagnose

**Maintenance:**
- maintain, maintenance, service

**Wiring:**
- wiring, electrical, connect, wire

**Procedures:**
- remove, replace, disassemble
- ground, grounding, seal, sealing
- procedure, steps, instructions
- "how to", "how do", "what are the steps"

### Format Rules for PDF-Detail Responses

1. **No Part Information Section** - Jumps straight to the PDF content
2. **Descriptive Headings** - Each excerpt gets a clear heading (e.g., "Installation Procedure")
3. **Page Numbers as Subheadings** - Format: `### Page X`
4. **Full Detail** - Complete information from the manual, not summarized
5. **Exact Content** - Only information from the PDF, nothing added
6. **Technical Precision** - All warnings, steps, specifications included

## Example Queries and Expected Outputs

### Example 1: Installation Query

**Input:** "How do I install part TRNPAN02916?"

**Output:**
```markdown
## Drain Pan Installation Instructions
### Page 12

[Full detailed installation steps from the manual]
- All safety warnings
- Step-by-step procedures  
- Torque specifications
- Sealing requirements
- Grounding instructions

## Post-Installation Verification
### Page 13

[Complete verification steps]
```

---

### Example 2: Specifications Query

**Input:** "What are the specifications for TRNPAN02916?"

**Output:**
```markdown
## Drain Pan Specifications
### Page 8

Material: 22-gauge galvanized steel
Dimensions: 24" L x 18" W x 2" D
Capacity: 1.5 gallons
Weight: 4.2 lbs
Drain outlet: 3/4" NPT

Temperature rating: -20°F to 150°F
Operating pressure: Atmospheric
Compliance: UL 1995, CSA C22.2

## Material Specifications
### Page 9

[Additional material details and certifications]
```

---

### Example 3: Troubleshooting Query

**Input:** "How to troubleshoot TRNPAN02916?"

**Output:**
```markdown
## Troubleshooting Guide
### Page 45

SYMPTOM: Water leakage around drain pan

POSSIBLE CAUSES:
1. Improper sealant application
2. Loose mounting hardware
3. Cracked pan (inspect for damage)
4. Blocked drain line

CORRECTIVE ACTIONS:
1. Inspect sealant - reapply if necessary
2. Check all fasteners - torque to 45 in-lbs
3. Replace pan if cracked or corroded
4. Clear drain line obstruction

## Leak Detection Procedure
### Page 46

[Step-by-step leak detection and repair procedure]
```

## Comparison Table

| Query Type | Intent | Format | Part Info | PDF Format |
|------------|--------|--------|-----------|------------|
| "Tell me about part X" | `part_info` | Current | ✅ Shown | Numbered list summary |
| "Tell me about model Y" | `model_info` | Current | ❌ Hidden | N/A |
| "How to install part X" | `pdf_detail` | **NEW** | ❌ Hidden | Detailed with headings |
| "What are specs for X" | `pdf_detail` | **NEW** | ❌ Hidden | Detailed with headings |

## Technical Implementation

### Query Parser Changes

**File:** `query_engine/query_parser.py`

Added PDF detail keyword detection:
```python
pdf_detail_keywords = [
    'install', 'installation', 'setup',
    'specification', 'specs', 'dimensions',
    'troubleshoot', 'repair', 'fix',
    # ... more keywords
]

if has_pdf_keywords and has_entity:
    return 'pdf_detail'
```

### Response Builder Changes

**File:** `query_engine/response_builder.py`

Added conditional formatting based on `query_intent`:
- `part_info` → Current format (Part Info + numbered excerpts)
- `model_info` → Current format (Model Info)
- `pdf_detail` → **NEW format** (Detailed excerpts with headings)

## Benefits

✅ **Preserves Existing Formats** - Part and model queries work exactly as before  
✅ **Deep PDF Information** - Detailed technical content when needed  
✅ **Intelligent Detection** - Automatically chooses the right format  
✅ **Complete Information** - No summarization for technical queries  
✅ **Professional Formatting** - Clear headings and structure  

## Testing

### Test General Part Query:
```
"Tell me about part TRNPAN02916"
```
Expected: Part Information + numbered PDF excerpts

### Test PDF-Specific Query:
```
"How do I install part TRNPAN02916?"
```
Expected: Detailed installation instructions with headings and page numbers

### Test Model Query:
```
"Tell me about model thc036e1e0a00a00000000000"
```
Expected: Model Information with parts list

## Files Modified

1. **`query_engine/query_parser.py`**
   - Added PDF detail keyword detection (lines 140-150)
   - Added `pdf_detail` intent (line 158)

2. **`query_engine/response_builder.py`**
   - Updated system prompt with PDF-specific format rules (lines 189-198, 217-226)
   - Added format distinction based on query intent

## Result

Your system now provides three distinct response formats optimized for different query types:
- 📋 **General info** → Quick overview with summaries
- 🔧 **Technical details** → Complete manual information
- 📦 **Model info** → Parts listings and relationships


