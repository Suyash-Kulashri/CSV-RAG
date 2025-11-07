# Content Accuracy Policy

## Philosophy: Clarity + Accuracy

This system follows a balanced approach:

✅ **Organize for Readability** - Structure content to be clear and understandable  
✅ **100% Accurate Content** - Every fact MUST come from the provided data  
❌ **No Fabrication** - Never add information not in the source  

---

## What This Means

### ✅ ALLOWED: Restructuring for Clarity

The system can and should:
- Create clear section headings
- Use bullet points and numbered lists
- Break dense paragraphs into logical sections
- Add formatting (bold, emphasis)
- Organize information by topic
- Make technical content more understandable

**Example:**

**Original PDF Text (Dense):**
```
When zone temperature rises above cooling setpoint RTRM energizes K10 relay coil 
closing K10 contacts energizing CC2 bringing on CPR2 if cooling requirement not 
satisfied RTRM energizes K9 relay de-energizes K10 bringing on CPR1 turning off 
CPR2 if still not satisfied both K9 and K10 energized both compressors on.
```

**System Output (Organized):**
```markdown
## Three-Stage Cooling Operation

**First Stage:**
- Zone temperature rises above cooling setpoint
- RTRM energizes K10 relay coil
- K10 contacts close
- CC2 is energized
- CPR2 compressor turns on

**Second Stage:**
- RTRM energizes K9 relay
- K10 is de-energized
- CPR1 compressor turns on
- CPR2 turns off

**Third Stage:**
- Both K9 and K10 are energized
- Both compressors (CPR1 and CPR2) turn on
```

**Why This is OK:**
- ✅ All information comes from the excerpt
- ✅ Nothing is added or inferred
- ✅ Much easier to understand
- ✅ Maintains technical accuracy

---

### ❌ FORBIDDEN: Adding Information

The system must NEVER:
- Add steps not mentioned in the PDF
- Infer missing details
- Include "typical" or "standard" procedures
- Use general HVAC knowledge to fill gaps
- Combine information from unrelated sources
- Create content not in the excerpt

**Example:**

**PDF Excerpt:**
```
Before drain pan removal, the switch wire must be disconnected.
```

**❌ BAD Output (Fabricated):**
```markdown
## Drain Pan Removal

**Pre-Removal Checklist:**
- Turn off power to the unit
- Verify all electrical connections
- Check for water in the pan
- Wear appropriate PPE

**Removal Steps:**
1. Disconnect the switch wire
2. Remove mounting screws
3. Carefully lift the drain pan
```

**Why This is BAD:**
- ❌ "Turn off power" - not in excerpt
- ❌ "Verify connections" - not in excerpt
- ❌ "Check for water" - not in excerpt
- ❌ "Wear PPE" - not in excerpt
- ❌ "Remove mounting screws" - not in excerpt
- ❌ "Carefully lift" - not in excerpt

**✅ GOOD Output (Accurate):**
```markdown
## Drain Pan Removal
### Page 30

Before drain pan removal, the switch wire must be disconnected.

*Note: The provided excerpt does not include complete removal steps. For full 
instructions, refer to the manual.*
```

**Why This is GOOD:**
- ✅ Only uses information from excerpt
- ✅ Honest about missing information
- ✅ Doesn't fabricate additional steps

---

## Verification Guidelines

### How to Check if Content is Accurate

#### 1. **Trace Every Statement**
Every bullet point, step, or detail should be traceable to the PDF excerpt.

**Test:**
- Pick any statement from the response
- Find it in the provided context
- If you can't find it → fabrication

#### 2. **Check for Generic Language**
Watch for phrases that sound generic or "common sense":
- ❌ "Ensure proper ventilation"
- ❌ "Follow safety procedures"
- ❌ "Check manufacturer specifications"
- ❌ "Verify connections are secure"

**Unless these exact phrases are in the PDF**, they're fabricated.

#### 3. **Look for Added Structure**
Acceptable:
- ✅ Organizing mentioned items into bullets
- ✅ Creating headings for topics discussed in PDF
- ✅ Breaking long sentences into clear steps

Not Acceptable:
- ❌ Adding steps between mentioned steps
- ❌ Creating sections for topics not in PDF
- ❌ Inferring "obvious" steps

#### 4. **Count the Facts**
- Count technical details in the response
- Count technical details in the excerpt
- Response should NOT have more facts than excerpt

---

## Examples from Your System

### Example 1: Unit Start-Up (Page 42)

**Query:** "Describe the unit start-up sequence"

**If Page 42 mentions:**
- Control options (electromechanical or ReliaTel)
- Three stages with K9, K10 relays
- CPR1, CPR2, CC1, CC2 components
- RTRM functionality

**System Can Show:**
```markdown
## Unit Start-Up Sequence
### Page 42

**Control Options:**
Units are offered with electromechanical or ReliaTel™ control options.

**Three-Stage Cooling Operation:**

*First Stage:*
- RTRM energizes K10 relay coil
- K10 contacts close
- CC2 is energized
- CPR2 compressor turns on

*Second Stage:*
[etc., organized from excerpt]
```

**System Cannot Add:**
- ❌ "Pre-start checklist"
- ❌ "Safety warnings" (unless in excerpt)
- ❌ "Typical start-up time: 5 minutes"
- ❌ "Ensure proper refrigerant levels"

---

### Example 2: Drain Pan Installation (Page 30)

**If Page 30 mentions:**
- Switch wire disconnection
- Grounding requirements
- Copper conductors

**System Can Show:**
```markdown
## Drain Pan Installation and Removal
### Page 30

**Electrical Requirements:**
- Disconnect switch wire before removal
- Proper grounding is required
- Use copper conductors for connections

**Air Sealing:**
- Prevent air leakage during installation
```

**System Cannot Add:**
- ❌ "Use 10-32 mounting screws" (unless mentioned)
- ❌ "Torque to 45 in-lbs" (unless mentioned)
- ❌ "Wait 10 minutes before..." (unless mentioned)

---

## The Key Distinction

### Formatting vs. Fabrication

**Formatting (ALLOWED):**
```
Original: "RTRM energizes K10 then CC2 then CPR2"
Formatted: "- RTRM energizes K10
            - CC2 is energized
            - CPR2 starts"
```
Same information, clearer presentation.

**Fabrication (FORBIDDEN):**
```
Original: "RTRM energizes K10 then CC2 then CPR2"
Fabricated: "- Check power supply
             - Verify K10 relay is functional
             - RTRM energizes K10
             - Monitor voltage at CC2
             - CC2 is energized
             - Check CPR2 start sequence
             - CPR2 starts"
```
Added information not in original.

---

## Quality Checklist

Before accepting a response as accurate, verify:

- [ ] **Every fact is traceable** - Can find each detail in the context
- [ ] **No generic additions** - No "typical" or "standard" statements
- [ ] **No inferred steps** - No steps added "for completeness"
- [ ] **Structure helps clarity** - Organization aids understanding
- [ ] **Honest about gaps** - States when information is incomplete
- [ ] **Page numbers cited** - Source is always referenced

---

## When to Report Issues

### Report if you see:

1. **Steps that seem too perfect**
   - 10-step procedures when PDF only mentions 3
   - Detailed checklists not in the excerpt

2. **Generic safety warnings**
   - "Wear appropriate PPE"
   - "Follow OSHA guidelines"
   - Unless explicitly in the PDF

3. **Technical specs not cited**
   - Torque values, dimensions, voltages
   - Unless from the excerpt

4. **Connecting words that add meaning**
   - "First, ensure..." (when PDF just says "ensure")
   - "After completing X, proceed to Y" (when PDF doesn't say "after")

---

## Summary

### The Goal
**Make technical content clear and understandable WITHOUT adding information that isn't there.**

### The Rule
**Every fact must have a source. Every detail must be from the excerpt. Structure for clarity, but never fabricate.**

### The Result
**Responses that are:**
- ✅ Well-organized and easy to read
- ✅ 100% accurate to source material
- ✅ Honest about missing information
- ✅ Helpful without being misleading

---

## For Developers

This policy is enforced through:
- System prompt in `response_builder.py` (lines 166-320)
- Query intent detection in `query_parser.py`
- Context building in `response_builder.py` (_build_context method)
- Multiple examples in the prompt showing good vs bad behavior

Temperature: 0.0 (maximum determinism)

---

**Last Updated:** November 7, 2025  
**Policy Status:** Active and Enforced

