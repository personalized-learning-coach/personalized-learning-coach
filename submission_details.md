# Kaggle Submission Details

Here is the content you can copy-paste into your Kaggle submission form.

## Basic Details

**Title**: Personalized Learning Coach

**Subtitle**: An AI-powered tutor that creates adaptive weekly plans, delivers interactive lessons, and tracks your progress using Google's Agent Development Kit.

## Project Description

### What I Built
I built the **Personalized Learning Coach** to make high-quality, 1-on-1 tutoring accessible to everyone. Most AI chatbots just answer questions, but I wanted to create something that acts like a real educational team. It proactively plans your curriculum, teaches you new concepts, tests your knowledge, and keeps you motivated along the way.

It uses a **custom agentic architecture** that I built using patterns from the Google Agent Development Kit (ADK). The whole system is powered by the new **Gemini 2.0 Flash** model.

### Architecture & Agents
The system is built around a "hub-and-spoke" design managed by a central **Orchestrator Agent**:

1.  **Orchestrator Agent**: This is the central brain of the app. It figures out what you want to do (like "I want to learn Python") and routes you to the right specialist.
2.  **Planner Agent**: Think of this as the curriculum director. It looks at your goals and creates a structured 4-week learning plan for you, complete with **weekly topics** and difficulty levels.
3.  **Tutor Agent**: This is your subject matter expert. It delivers interactive lessons and explains complex ideas using simple analogies. It also creates practice problems on the fly and uses a "Socratic" style to help you really understand the material.
4.  **Assessment Agent**: This is the examiner. It runs quick quizzes to see what you already know so you don't waste time. It also checks your progress at the end of each week.
5.  **Coach Agent**: This is your cheerleader. It tracks your progress and celebrates your wins. If you get stuck or feel unmotivated, it steps in to help you keep going.
6.  **Progress Agent**: The historian. It tracks your long-term journey, ensuring that completed weeks are saved and that you can pick up exactly where you left off.

### Key Features
*   **Personalized Pacing**: You can move through the weeks at your own speed. The system tracks your progress and only advances when you are ready.
*   **Persistent Memory**: The system remembers you. It keeps track of your chat history, completed weeks, and quiz scores even if you refresh the page or come back later.
*   **Structured Learning**: Instead of an endless chat window, your learning is organized into clear "Weeks" and "Topics" so you can see your progress.
*   **Interactive Quizzes**: You get real-time feedback on multiple-choice questions, with clear explanations for why an answer is right or wrong.

### Technology Stack
*   **Architecture**: I built a custom Orchestrator using ADK patterns to make it work smoothly with Streamlit.
*   **Model**: I used Gemini 2.0 Flash via the `google-genai` SDK because it provides high-speed reasoning with low latency.
*   **Frontend**: The UI is built with Streamlit to be clean and interactive.
*   **Deployment**: The app is hosted on Streamlit Community Cloud, with API keys managed securely.

### How It Works
1.  **Onboarding**: You select a topic you want to learn, like "Data Structures".
2.  **Assessment**: The Assessment Agent gives you a quick diagnostic quiz.
3.  **Planning**: The Planner Agent creates a custom 4-week schedule based on how you did.
4.  **Learning**: You click "Start Lesson" and the Tutor Agent takes over to teach you the material.
5.  **Review**: At the end of the week, you take a milestone quiz to unlock the next module.

This project shows how **agentic workflows** can go beyond simple Q&A to build a system that can plan, execute, and adapt over time.

## Project Links

**GitHub Repository**:
`https://github.com/personalized-learning-coach/personalized-learning-coach`

**Live Demo**:
`https://personalized-learning-coach-4id8s43gx2grzuhkpviaav.streamlit.app/`
