# Capstone Video Script (3 Minutes)

## 0:00 - 0:30: The Problem (Hook)
**Visual**: Show a messy desktop with open tabs for "Python tutorial", "Java course", "Calendar", and a confused user face (or stock image).
**Audio**: 
"We've all been there. You want to learn a new skill, but you're drowning in resources. You don't know where to start, you lose motivation, and you have no one to tell you *why* you're stuck. Self-directed learning is broken because it lacks structure and feedback."

## 0:30 - 1:00: The Solution (Agents)
**Visual**: Screen recording of the **Personalized Learning Coach** landing page.
**Audio**:
"Meet the Personalized Learning Coach. It's not just a chatbot; it's a team of AI agents working together to build your perfect curriculum. Instead of a generic answer, you get a Planner, a Tutor, and an Assessor, all dedicated to your success."

## 1:00 - 1:45: Architecture (How it Works)
**Visual**: Show the **Mermaid Diagram** from the README (Orchestrator -> Planner/Tutor/Assessment). Zoom in on each agent as mentioned.
**Audio**:
"We built this using a multi-agent architecture. 
- The **Orchestrator** manages the conversation and context.
- The **Planner** designs a week-by-week schedule based on your goals.
- The **Assessment Agent** runs interactive quizzes and—crucially—remembers your mistakes in a 'Mistake Bank' to help you review later.
- And the **Tutor** delivers bite-sized lessons using Google Search for up-to-date info."

## 1:45 - 2:30: Demo (The "Wow" Moment)
**Visual**: Fast-paced screen recording:
1.  User types: "I want to learn Python." -> System generates a plan.
2.  User clicks "Start Week 1".
3.  User takes a quiz and **gets a question wrong**.
4.  Show the system saying: "I noticed you struggled with Loops. Let's review that." (The Mistake Bank in action).
**Audio**:
"Watch as I ask to learn Python. Instantly, I get a structured plan. But here's the magic: when I take a quiz and get a question wrong, the system *remembers*. It adapts future lessons to target my weak spots, just like a real human coach would."

## 2:30 - 3:00: The Build & Conclusion
**Visual**: Quick flash of VS Code showing `Dockerfile`, `traces.jsonl`, and the code structure.
**Audio**:
"We built this with Python and Google Gemini, using Docker for easy deployment and comprehensive tracing for observability. The Personalized Learning Coach turns the chaos of self-learning into a clear path to mastery. Try it out on GitHub today."
