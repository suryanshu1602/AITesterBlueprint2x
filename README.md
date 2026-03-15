# Automation Desktop Blueprint by 2x - SDAT Course

Welcome to the **Automation Desktop Blueprint by 2x** repository! This project serves as a comprehensive guide to understanding and integrating Artificial Intelligence (AI) and Large Language Models (LLMs) into modern software testing and Quality Assurance (QA) workflows.

The repository is structured systematically into chapters, covering theoretical concepts, practical exercises, and real-world projects.

## Learning Methodology

To get the most out of this repository, follow this workflow for each chapter:

1. **Core Concepts (`core_concepts/`)**: Start here. These folders contain the foundational theory, terminology, and key concepts of the chapter. Read these markdown files to build your knowledge base.
2. **Templates & Rules (`rules_checklists/`, `templates/`)**: Utilize reusable templates and strict rules (e.g., Anti-Hallucination guidelines, BLAST) to enforce consistency and quality in your AI interactions.
3. **Practical Guides & Techniques (`practical_guides/`, `techniques/`)**: Move to these folders to see how the theoretical concepts are applied in practice. This includes prompt strategies, frameworks (like RICE-POT), and step-by-step tutorials.
4. **Learning Process & Exercises (`learning_practice/`)**: Put your knowledge to the test. These folders contain hands-on, self-directed exercises and solutions to reinforce what you've learned.
5. **Projects (`Project_.../`)**: Finally, apply everything you have learned to comprehensive, real-world testing automation challenges and frameworks. 

---

## Course Curriculum Overview

### 📖 Chapter 1: LLM Basics (`Chapter_01_LLM_BASICS/`)
In this foundational chapter, we explore the basics of Large Language Models (LLMs) and how to leverage local/remote LLMs for generating deterministic test automation scripts. We establish strict rules (like the Anti-Hallucination rules and B.L.A.S.T. master system prompt) to prevent AI drift or fabricated outputs.

| Category | Folder / Module | Description |
| :--- | :--- | :--- |
| **Learning** | `core_concepts/` | Architectural fundamentals of Foundation Models and what LLMs are. |
| **Learning** | `practical_guides/` | Practical guidance on setting up and interacting with LLMs locally and via APIs. |
| **Learning** | `learning_practice/` | Exercises for establishing baseline LLM interaction skills. |
| **Learning** | `rules_checklists/` | Critical guardrails like the Anti-Hallucination rule-sets and B.L.A.S.T. framework. |
| **Project** | `Project_01_LocalLLMTestGenerator` | Building a standard standalone local test generator application. |
| **Project** | `Project_01_LocalLLMTestGenerator_Antigravity` | A specialized test generator built utilizing an advanced agentic system. |
| **Project** | `LocalLLMTestGenBuddy` | Submodule component utilized for local test generation contexts. |

---

### 📖 Chapter 2: Prompt Engineering (`Chapter_02_PROMPT_ENGINEERING/`)
This chapter dives into the art and science of **Prompt Engineering** in automation. We introduce prompt frameworks like **RICE-POT** (Role, Instructions, Context, Example, Parameters, Output, Tone) and use them to generate enterprise-grade automation frameworks, ensuring zero bad coding practices and strict compliance with production-level standards.

| Category | Folder / Module | Description |
| :--- | :--- | :--- |
| **Learning** | `core_concepts/` | The anatomy of a prompt, prompt frameworks (STAR, CLEAR, CRISP), and prompt engineering introduction. |
| **Learning** | `techniques/` | Advanced techniques such as Few-Shot, Chain-of-Thought, Zero-Shot, and Role-playing. |
| **Learning** | `practical_guides/` | Step-by-step guides to writing your first QA prompts and instructions. |
| **Learning** | `learning_practice/` | Hands-on prompt engineering exercises and their documented solutions. |
| **Project** | `Project_02_Prompt_Templates` | A repository of reusable, high-quality prompt templates for QA (API, UI, Bug Reports). |
| **Project** | `Project_02_REAL_PROJECT_PE` | Applying prompt engineering to a real-world project (VWO Platform Test Plan & Analysis). |
| **Project** | `Project_02_RICE_POT_Selenium_FW` | Generating an enterprise-grade Selenium TestNG Page Object Model framework. |
| **Project** | `Project_03_RICE_POT_Playwright_Advance_FQ` | Advanced prompt engineering extended into architectural end-to-end testing with Playwright. |
