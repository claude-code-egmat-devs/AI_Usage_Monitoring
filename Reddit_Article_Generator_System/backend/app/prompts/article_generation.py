"""
Article Generation Prompts extracted from n8n workflows
"""

# Main article generation prompt for RC section
RC_ARTICLE_PROMPT = """GMAT RC Article Creation Framework

Goal

Create an article that a Harvard educator would be proud of that explains to GMAT Test takers, why they make a mistake in GMAT RC, and give them a framework to approach to avoid making these mistakes.

Important: Make sure that the article is generic. It should talk about general mistakes/principles and not be specific to just that passage.

Opening Requirements

Start with a generic hook about the universal principle or challenge being discussed. Do NOT reference the specific passage, question, or any passage-specific content in the opening paragraphs. The opening should apply to all similar GMAT RC situations and establish the conceptual framework before any examples.

VARY THE OPENING – DO NOT USE THE SAME STANDARD OPENING FOR EACH ARTICLE.

Process Overview

Step 1: Do a Diagnosis

You will receive the following inputs:

    A hard RC passage

    A Hard question on that passage

    The stats of the question

    The solution (detailed)

    The most popular incorrect choice

Your Process (do not publish):

    Identify why people make the mistake, that is why do they choose the incorrect choice. You will evaluate one of more of the following:

    Where does their thought process go wrong?

    Do they make a conceptual error, such as presuming that the author is making a claim or backing a piece of information when the author is merely presenting information, or misinterpreting the role of the evidence that the author presents, etc.

    Avoid doing things critical to RC passage, such as visualization, connecting pieces of information despite the presence of markers, or not drawing combination inferences, etc.

Your goal is to identify a primary reason as to why people chose the incorrect choice and rejected the correct choice. Iterate and Dwell upon if needed here.

Step 2: Strategize How to Teach This Aspect

Once you have narrowed down, strategize how to make the reader realize his mistake.

    Explain the core principle using a simple example - keep this generic

    Explain how this is tested in a generic sense (remember, the student has not read the reference passage)

    Give example (use the provided passage as reference - remember - they do not have it yet). Elaborate on the %age of people who make this mistake. This example needs to be a simple 2-3 line passage, to corroborate the issue being discussed in the article.

Good Example: "Many companies have implemented open office designs, which feature shared workspaces and minimal barriers between employees. However, recent productivity studies show these designs actually decrease employee focus by 15%. This challenges the assumption that open offices improve collaboration."

Step 3: Create a Framework to Enable the Student to Avoid Making This Mistake

    Create the framework

    Explain the framework using a simple example

Step 4: Create Two Exercises

    Simple Example (two-line passage)

    Complex Example (4-line passage)

Step 5: Evaluate the Article You Generated

    Revise every aspect of it. Make sure that the article is generic. It should talk about general mistakes/principles and not be specific to just that passage

    Ensure your framework and principles can be applied to other similar RC passages, not just this specific one

    If you enhance the output of one step, then check its potential impact on next step

    Rate this article for clarity. How would a Harvard educator rate this.

Step 6: Final Evaluation

Go back and evaluate the article if it is following all the best practices:

    Opening - needs to be generic and attractive to make the reader want to read the article, but relevant to the problem discussed at hand.

    The example used needs to be simple and should help explain the problem at hand.

    The framework explained needs to be pertinent to the problem at hand, and relevant and applicable to the strategy to overcome the problem.

    The practice examples need to be relevant and applicable to the concept being taught.

Example of good example:

A Simple Example

Imagine reading this brief passage:

"Many companies have implemented open office designs, which feature shared workspaces and minimal barriers between employees. However, recent productivity studies show these designs actually decrease employee focus by 15%. This challenges the assumption that open offices improve collaboration."

Why is this good - it can help students visualize the problem at hand, and is relevant to the concept being described in the article.

If the best practices are not met, make the changes and present the final article."""


def get_article_generation_prompt(
    passage_text: str,
    question_text: str,
    question_stats: str,
    detailed_solution: str,
    popular_incorrect_choice: str,
) -> str:
    """
    Build the full article generation prompt with reference questions.

    Args:
        passage_text: The RC passage text
        question_text: The question text
        question_stats: Statistics about the question
        detailed_solution: Detailed solution explanation
        popular_incorrect_choice: The most popular incorrect answer

    Returns:
        Complete prompt for article generation
    """
    reference_questions = f"""Passage Text:

{passage_text}

Question Text:

{question_text}

Question Stats:

{question_stats}

Detailed Solution:

{detailed_solution}

Popular Incorrect Choice marked by the students:

{popular_incorrect_choice}"""

    return f"""You are an expert GMAT educator tasked with creating high-quality articles that help students avoid common Reading Comprehension mistakes. You will analyze the provided reference questions and create an educational article following a specific framework.

Reference Questions to Analyze:
{reference_questions}

Instructions
{RC_ARTICLE_PROMPT}


OUTPUT FORMAT:
Return a JSON object with exactly these two attributes:

{{
  "analysis_and_approach": "Detailed analysis of why students make this mistake, the teaching strategy, and framework rationale. Include the primary error identified and pedagogical approach chosen.",
  "generated_article": "Complete article text following the framework structure, with clear sections, examples, and actionable guidance for students."
}}"""


# Generic article generation prompt template
ARTICLE_GENERATION_PROMPT = """You are an expert GMAT educator. Create a high-quality educational article based on the provided reference material.

The article should:
1. Start with a generic, engaging hook
2. Explain the core concept using simple examples
3. Provide a clear framework for students to follow
4. Include practice exercises
5. Be generic and applicable to similar problems

OUTPUT FORMAT:
Return a JSON object with:
{{
  "analysis_and_approach": "Your analysis and teaching strategy",
  "generated_article": "The complete article text"
}}"""
