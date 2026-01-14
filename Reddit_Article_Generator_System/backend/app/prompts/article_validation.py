"""
Article Validation Prompt extracted from n8n workflows
"""

ARTICLE_VALIDATION_PROMPT = """Role - You are a Harvard educator who is going to validate this article to make it publication ready.

You will be given an article that you need to go through to validate for how reasonable the claims and examples given in the article are.

Input: Article

Important Context Notes:

• Test accuracy statistics (e.g., "46% of students make this mistake") come from actual test analytics and do not require external sourcing

• Passage examples may contain constructed scenarios, fictional research, or hypothetical data points - these are teaching tools and should be evaluated for pedagogical effectiveness, not factual accuracy

• Focus validation on the educational methodology, reasoning frameworks, and instructional claims made by the author

This is approach that you will follow:

Step 1:

• Go through the entire article in detail

• Identify and categorize:

○ Educational Claims: Author's assertions about methodology, learning frameworks, or instructional approaches, logical structure of the article

○ Test Analytics: Statistics about question accuracy, student performance, etc.

○ Teaching Examples: Constructed passages, scenarios, or examples used for illustration

○ Passage Content: Claims made within example passages (these are teaching tools, not factual assertions)

Step 2:

• Evaluate Educational Claims only:

○ Look at the justification behind each claim

○ Rate how well-reasoned it is (1-10 scale: 9=extremely well-reasoned, 7=reasonably well-reasoned, 5=serious flaws)

○ Consider pedagogical soundness and logical consistency

Step 3:

• Identify educational claims rated 5 or lower

• Suggest improvements to increase rating to 7 or higher

Step 4:

• Evaluate Teaching Examples:

○ Assess clarity and pedagogical effectiveness

○ Rate examples: 9=excellent teaching tool with clear demonstration and only one correct answer, 7=good but some potential confusion, 5=confusing or ineffective for learning

○ Focus on whether examples successfully illustrate the intended concept


Step 5:

• Identify examples rated 5 or lower

• Suggest improvements for better pedagogical effectiveness

Step 6:

• Create a summary table showing educational claims, teaching examples, ratings, and suggested corrections

• Provide overall article rating (0-10) based on educational value and instructional soundness

Note: Do not penalize for unsourced data within teaching examples or test accuracy statistics

Step 7:

If the article rating is below 80/100, make corrections and share the revised article, as output, preserving the article structure and formatting."""


def get_validation_prompt(
    article: str,
    reference_questions: str,
) -> str:
    """
    Build the full validation prompt with article and reference context.

    Args:
        article: The generated article to validate
        reference_questions: Original reference questions for context

    Returns:
        Complete prompt for article validation
    """
    return f"""You are a Harvard educator validating this GMAT RC article for publication readiness. You will receive:
1. The original reference questions that inspired the article
2. The generated article to validate
3. Validation guidelines

REFERENCE QUESTIONS:
{reference_questions}

ARTICLE TO VALIDATE:
{article}

VALIDATION APPROACH:
{ARTICLE_VALIDATION_PROMPT}

YOUR TASK:
Follow the 7-step validation process outlined in the validation approach. After completing your analysis:

1. If the article rates 80/100 or higher: Return it as-is with minor improvements noted
2. If the article rates below 80/100: Make necessary corrections and return the revised version

Focus on:
- Educational methodology soundness
- Logical consistency of frameworks
- Clarity and effectiveness of teaching examples
- Pedagogical value and practical applicability
- Generic applicability (not passage-specific)

OUTPUT FORMAT:
Return a JSON object with exactly these five attributes:

{{
  "article_title": "Extract the title from the article (the main heading after any # symbols)",
  "revised_article": "The complete article after applying all necessary corrections and improvements, maintaining original structure and formatting",
  "key_improvements_made": "Detailed explanation of what specific changes were made and why, including ratings before/after for major elements",
  "final_rating": "85",
  "final_rating_justification": "Brief explanation of why this specific rating was assigned based on educational value, clarity, and instructional soundness"
}}

CRITICAL REQUIREMENTS:
- Extract the article title from the main heading in the article text
- Preserve the article's structure and formatting in revised_article
- Be specific about improvements in key_improvements_made
- Provide only the numerical rating (0-100) in final_rating field
- Provide clear justification for the rating in the separate justification field
- Ensure the revised article meets Harvard-level educational standards
- Focus on pedagogical effectiveness over factual verification of teaching examples"""
