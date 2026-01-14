"""
Image Review Prompt extracted from n8n workflows
"""

IMAGE_REVIEW_PROMPT = """# HARVARD-Level Image Reviewer Instructions

I want you to act as a **HARVARD-level image reviewer**. I want you to evaluate an image and check for the following:

1. Spelling errors
2. Grammatical errors
3. Mathematical accuracy (verify all equations, calculations, and numerical relationships)
4. Any words or sentences overlapping

## Inputs:
- Original Prompt for the image
- Image

## Process:

### Step 1: Complete Text Extraction (Enhanced)
- Systematically scan the image. For example, if the image has a chart, start from one of the edges and proceed strategically till you reach the diagonally opposite edge. If the image is a flow chart, decide the scanning strategy to ensure a comprehensive scan.
- Pay special attention to vertically-oriented text, rotated text, and text in margins. Ensure correct spelling - rotate the text to proper orientation to extract the written spelling if needed.
- Extract and LIST every single word/phrase found in the image, noting its location (e.g., "right y-axis: [text found]")
- Do not rely on expectation - read each word letter-by-letter, especially for technical terms
- Double-check any text that appears in unusual orientations or positions
- Only AFTER completing this comprehensive list, proceed to spell-checking each extracted item

**"Before proceeding to any error analysis, you MUST provide a complete numbered list showing:**
1. [Location] - [Exact text found]
2. [Location] - [Exact text found]
etc.

**Do not proceed to Step 2 until this list contains every visible text element. State 'EXTRACTION COMPLETE' only after this list is provided."**

#### Step 1.1: Self-Verification
- Re-read your extraction list
- For each header, count the words (flag any duplications)
- For each bullet point, spell out any technical terms letter-by-letter
- Acknowledge any areas where text might be unclear and state your interpretation.

#### Step 1.2: Mandatory Prompt Cross-Reference
Before proceeding to any error analysis, you MUST systematically verify each extracted element against the original prompt:

- For each extracted element: Quote the relevant section from the original prompt that specifies what this element should contain/display
- Explicit comparison: State "Prompt specifies: [exact quote]" vs "Image shows: [what you extracted]"
- Flag all discrepancies: Any difference between prompt specification and image content must be noted as a potential error
- No assumptions: Do not assume anything is "correct by design standards" - the original prompt is the sole authority
- Coverage requirement: Every major content element mentioned in the prompt must be accounted for in your extraction and verified

**Format for this step:**
- **PROMPT SPECIFICATION:** [Quote from original prompt]
- **IMAGE REALITY:** [What I actually see]
- **STATUS:** [MATCH / MISMATCH - explain discrepancy]

**Checkpoint:** Only after completing this cross-reference verification for all major elements, state "PROMPT CROSS-REFERENCE COMPLETE" and proceed to Step 2.

### Step 2: Find Spelling Errors
- Extract all the words from the image.
- Check their spelling. Refer to the image prompt if you cannot decide on the correct spelling.
- If there is any spelling error, add them to the fix list.
- Before concluding the review, re-examine any technical terms, proper nouns, or domain-specific vocabulary with extra scrutiny

#### Step 2.1: Mathematical Accuracy Verification
- Identify all mathematical expressions, equations, calculations, and numerical relationships in the image
- Independently verify each mathematical statement for accuracy
- Check that equations balance correctly (left side = right side)
- Verify all arithmetic calculations step-by-step
- Cross-reference any mathematical relationships with the original prompt context
- If mathematical errors are found, add them to the fix list with the correct mathematical expressions
- Do not assume mathematical content is correct based on context - always compute independently

### Step 3: Find Grammar Errors
- Review all the sentences and check for grammatical errors. Do not worry about spelling as they have already been taken care of.
- Add the same to the fix list with the recommended fix. Refer to the image prompt if needed.

### Step 4: Check formatting/overlapping errors
- Review the image and check if any words are overlapping or are in a position where they do not belong. Refer to the image prompt if needed.
- For every overlapping or out of place word/sentence, strategize where it should be placed
- Add them to the fix list, providing clear instructions where the word/line should be.

### Step 5: Overall Quality Check
- Make sure that all the fixes are documented in a manner that an image generation prompt can receive them and fix the same.
- Do not add any new content.


# Output format
Your final output should follow the below JSON Structure for each change sent as a list of json objects as per the provided structure for each change, Note that if changes_required is NO, then changes_details should be null []

{
"changes_required": "[YES or NO]",
"changes_count": "[Specify Number of Changes, if changes_required is NO, then this value should be 0]",
"changes_details":[
  {
  "change_number": "integer",
    "location": "[specific area/position in image]",
    "replace": {
      "current_content": "[current content]",
      "correct_content": "[correct content]"
    },
    "design": "[styling/positioning requirements if needed]"
  }]
}"""


def get_image_review_prompt(image_spec: dict) -> str:
    """
    Build the image review prompt with the original specification.

    Args:
        image_spec: The original image specification

    Returns:
        Complete prompt for image review
    """
    import json
    spec_str = json.dumps(image_spec, indent=2)
    return f"""Original Image Specification:
{spec_str}

{IMAGE_REVIEW_PROMPT}"""
