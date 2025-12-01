# app.py
import traceback
import streamlit as st
import json
from dotenv import load_dotenv

load_dotenv(".env.local")

st.set_page_config(page_title="Personalized Learning Coach", layout="centered")
st.title("Personalized Learning Coach")

try:
    from personalized_learning_coach.agents.orchestrator import OrchestratorAgent  # type: ignore
    ORCHESTRATOR_AVAILABLE = True
except Exception as e:
    ORCHESTRATOR_AVAILABLE = False
    orchestrator_import_error = e
    orchestrator_import_tb = traceback.format_exc()

# Initialize session state
if "chats" not in st.session_state:
    st.session_state.chats = {}  # {plan_id: [messages]}

# Global/Default chat for when no plan is active
if "default" not in st.session_state.chats:
    st.session_state.chats["default"] = []

if "messages" not in st.session_state:
    st.session_state.messages = [{"role":"system","text":"Chat with the Orchestrator. Ask for a plan, start lessons, or say 'done'."}]

if "orchestrator" not in st.session_state:
    if ORCHESTRATOR_AVAILABLE:
        try:
            if "user_id" not in st.session_state:
                import uuid
                st.session_state.user_id = str(uuid.uuid4())
            st.session_state.orchestrator = OrchestratorAgent(user_id=st.session_state.user_id)
        except Exception as e:
            st.session_state.orchestrator = None
            orchestrator_init_error = e
            orchestrator_init_tb = traceback.format_exc()
    else:
        st.session_state.orchestrator = None

if not ORCHESTRATOR_AVAILABLE:
    st.warning("OrchestratorAgent import failed — falling back to echo. Open terminal for full traceback.")
    with st.expander("Import error (click to view)"):
        st.code(orchestrator_import_tb)

if ORCHESTRATOR_AVAILABLE and st.session_state.orchestrator is None:
    st.warning("OrchestratorAgent failed to initialize. See details below.")
    with st.expander("Init error"):
        st.code(orchestrator_init_tb)


orch = st.session_state.orchestrator

# --- Sidebar for Plan & Progress ---
with st.sidebar:
    st.header("My Learning Paths")

    if orch: # Check if orchestrator is initialized before accessing its state
        # Get available plans
        plans = orch.state.get("plans", {})
        
        # 1. Plan Selection (Dropdown)
        plan_options = {p_id: p_data["main_topic"] for p_id, p_data in plans.items()}
        options_list = ["Create New / General"] + list(plan_options.values())
        
        active_id = orch.state.get("active_plan_id")
        current_selection_index = 0
        if active_id and active_id in plan_options:
            current_topic = plan_options[active_id]
            if current_topic in options_list:
                current_selection_index = options_list.index(current_topic)

        selected_option = st.selectbox(
            "Select Learning Path:",
            options_list,
            index=current_selection_index
        )

        # Handle Plan Switching
        if selected_option == "Create New / General":
            if active_id is not None:
                orch.state["active_plan_id"] = None
                st.rerun()
        else:
            # Find ID for selected topic
            target_id = None
            for pid, topic in plan_options.items():
                if topic == selected_option:
                    target_id = pid
                    break
            
            if target_id and target_id != active_id:
                orch.switch_plan(target_id)
                st.rerun()

        st.divider()

        # 2. Week Selection (Radio)
        ctx = orch.get_active_context()
        if ctx:
            st.subheader(f"Plan: {ctx.get('main_topic')}")
            
            plan_data = ctx.get("data", {})
            weeks = plan_data.get("weeks", [])
            if not weeks:
                # Fallback: Check top-level (Orchestrator stores it flat)
                weeks = ctx.get("weeks", [])
            
            if weeks:
                week_labels = []
                for i, w in enumerate(weeks):
                    topic = w.get("topic", "Unknown")
                    week_labels.append(f"Week {i+1}: {topic}")
                
                current_week_idx = ctx.get("active_week_index", 0)
                # Ensure index is valid
                if current_week_idx >= len(week_labels):
                    current_week_idx = 0
                
                # SYNC LOGIC: Backend -> Frontend
                # We track the last known backend index to detect updates (e.g. quiz pass)
                if "last_backend_week_idx" not in st.session_state:
                    st.session_state["last_backend_week_idx"] = current_week_idx
                
                # If backend index changed (and we didn't just switch it ourselves), sync frontend
                if current_week_idx != st.session_state["last_backend_week_idx"]:
                     if current_week_idx < len(week_labels):
                        st.session_state["week_selector"] = week_labels[current_week_idx]
                     st.session_state["last_backend_week_idx"] = current_week_idx
                
                # Callback for User Interaction
                def on_week_change():
                    selected = st.session_state.week_selector
                    if selected in week_labels:
                        new_idx = week_labels.index(selected)
                        orch.switch_week(ctx["id"], new_idx)
                        # Update tracker so we don't re-sync on next run
                        st.session_state["last_backend_week_idx"] = new_idx
                
                # Render Widget
                selected_week = st.radio(
                    "Select Week:",
                    week_labels,
                    index=current_week_idx, # Ignored after first render if key exists
                    key="week_selector",
                    on_change=on_week_change
                )
                
                # Determine index for display
                if selected_week in week_labels:
                    new_week_idx = week_labels.index(selected_week)
                else:
                    new_week_idx = current_week_idx

                # Show objectives for selected week
                st.info(f"**Current Focus:**\n{weeks[new_week_idx].get('topic')}")
                objs = weeks[new_week_idx].get("objectives", [])
                if objs:
                    st.markdown("**Objectives:**")
                    for o in objs:
                        st.markdown(f"- {o}")

            st.progress(ctx.get("progress", 0.0))
        else:
            st.info("No active plan selected. Ask to create one!")
    else:
        st.info("Orchestrator not available. Sidebar features are limited.")
# -----------------------------------

# Determine which chat history to show
chat_key = "default"
if orch:
    active_id = orch.state.get("active_plan_id")
    if active_id:
        # Key by Plan ID + Week Index
        ctx = orch.state["plans"].get(active_id, {})
        w_idx = ctx.get("active_week_index", 0)
        chat_key = f"{active_id}_w{w_idx}"

# Ensure chat history is loaded from persistence
if chat_key not in st.session_state.chats:
    st.session_state.chats[chat_key] = []
    
    if orch:
        # Load from Orchestrator persistence
        saved_chats = orch.get_chat_history(chat_key)
        if saved_chats:
            st.session_state.chats[chat_key] = saved_chats
        elif active_id:
             # Fallback: Try loading from plan data (legacy support)
            plan = orch.state["plans"].get(active_id)
            if plan and "chat_history" in plan:
                st.session_state.chats[chat_key] = plan["chat_history"].get(str(w_idx), [])

# Double check: If session state is empty but persistence has data (e.g. page refresh)
if not st.session_state.chats[chat_key] and orch:
     saved_chats = orch.get_chat_history(chat_key)
     if saved_chats:
         st.session_state.chats[chat_key] = saved_chats

current_messages = st.session_state.chats[chat_key]

# Display chat messages
for message in current_messages:
    role = message["role"]
    content = message.get("content") or message.get("text") or ""

    with st.chat_message(role):
        if role == "assistant":
            try:
                parsed = json.loads(content)
                st.code(json.dumps(parsed, indent=2, ensure_ascii=False))
            except (json.JSONDecodeError, TypeError):
                st.markdown(content)
        else:
            st.markdown(content)

# Check for active assessment
if orch and orch.state.get("assessment_in_progress"):
    assessment_data = orch.state.get("assessment_data", {})
    questions = assessment_data.get("questions", [])
    
    if questions:
        st.info("### Assessment In Progress\nPlease answer the following questions to complete this week.")
        
        with st.form("assessment_form"):
            answers = {}
            for i, q in enumerate(questions):
                qid = q.get("qid", f"q{i+1}")
                prompt = q.get("prompt", "")
                options = q.get("options")
                
                st.markdown(f"**{i+1}. {prompt}**")
                
                if isinstance(options, dict) and options:
                    # MCQ
                    opts = list(options.keys())
                    # Format options for display
                    format_func = lambda x: f"{x}) {options[x]}"
                    ans = st.radio(f"Select answer for Q{i+1}", opts, format_func=format_func, key=f"radio_{qid}", index=None)
                    answers[qid] = ans
                elif isinstance(options, list) and options:
                     # MCQ List
                     ans = st.radio(f"Select answer for Q{i+1}", options, key=f"radio_{qid}", index=None)
                     answers[qid] = ans
                else:
                    # Open ended
                    ans = st.text_area(f"Your answer for Q{i+1}", key=f"text_{qid}")
                    answers[qid] = ans
            
            submitted = st.form_submit_button("Submit Assessment")
            
            if submitted:
                # Serialize answers to JSON
                # st.sidebar.write("Debug Answers:", answers) # Uncomment for debugging
                payload = json.dumps(answers)
                
                # Add user message (hidden or summary)
                st.session_state.chats[chat_key].append({"role": "user", "content": "Submitted Assessment"})
                if orch:
                    orch.save_chat_history(chat_key, st.session_state.chats[chat_key])
                
                try:
                    # Run orchestrator with JSON payload
                    resp = orch.run(payload)
                    
                    # Display response
                    st.session_state.chats[chat_key].append({"role": "assistant", "content": str(resp)})
                    if orch:
                        orch.save_chat_history(chat_key, st.session_state.chats[chat_key])
                    
                    # Check if we advanced weeks (Assessment Passed)
                    new_active_id = orch.state.get("active_plan_id")
                    if new_active_id:
                        new_ctx = orch.state["plans"].get(new_active_id, {})
                        new_w_idx = new_ctx.get("active_week_index", 0)
                        new_chat_key = f"{new_active_id}_w{new_w_idx}"
                        
                        if new_chat_key != chat_key:
                            # We advanced! Force rerun to switch context immediately
                            st.rerun()

                    st.rerun()
                except Exception as e:
                    st.error(f"Error submitting assessment: {e}")

else:
    # Standard Chat Input
    if prompt := st.chat_input("Type your message..."):
        # Capture current key to prevent bleed if user switches tabs (though Streamlit handles this per session)
        current_key = chat_key 
        
        # Add user message to chat history
        st.session_state.chats[current_key].append({"role": "user", "content": prompt})
        if orch:
            orch.save_chat_history(current_key, st.session_state.chats[current_key])
            
        with st.chat_message("user"):
            st.markdown(prompt)

        # Process with Orchestrator
        reply_text = "Sorry — I couldn't process your request."
        if orch:
            try:
                with st.spinner("Thinking..."):
                    resp = orch.run(prompt)
                
                if isinstance(resp, dict):
                    reply_text = json.dumps(resp, ensure_ascii=False)
                else:
                    reply_text = str(resp)

                # Check if plan/week changed during run (e.g. created new plan or advanced week)
                new_active_id = orch.state.get("active_plan_id")
                
                # Determine TARGET chat key for response
                target_key = current_key
                if new_active_id:
                    new_ctx = orch.state["plans"].get(new_active_id, {})
                    new_w_idx = new_ctx.get("active_week_index", 0)
                    new_chat_key = f"{new_active_id}_w{new_w_idx}"
                    
                    # If we changed weeks/plans, the response belongs to the NEW context
                    if new_chat_key != current_key:
                        # Only switch if it's a week advancement within the SAME plan
                        # OR if it's a brand new plan creation (which we can infer if current was 'default')
                        if new_active_id == active_id or current_key == "default":
                             target_key = new_chat_key
                             
                             # SYNC SIDEBAR: Update the radio button state to match the new week
                             # This prevents the sidebar from reverting the week on the next run
                             if new_active_id == active_id:
                                 # Reconstruct the label (assuming format matches sidebar)
                                 # We need the topic.
                                 new_weeks = new_ctx.get("data", {}).get("weeks", [])
                                 if new_w_idx < len(new_weeks):
                                     new_topic = new_weeks[new_w_idx].get("topic", "Unknown")
                                     new_label = f"Week {new_w_idx+1}: {new_topic}"
                                     st.session_state["week_selector"] = new_label

                # Ensure target chat exists
                if target_key not in st.session_state.chats:
                    st.session_state.chats[target_key] = []
                    saved = orch.get_chat_history(target_key)
                    if saved:
                         st.session_state.chats[target_key] = saved

                # Add response to TARGET chat
                st.session_state.chats[target_key].append({"role": "assistant", "content": reply_text})
                orch.save_chat_history(target_key, st.session_state.chats[target_key])

                # If we switched FROM default (General) to a specific plan, CLEAR default chat
                if current_key == "default" and target_key != "default":
                    st.session_state.chats["default"] = []
                    orch.save_chat_history("default", [])

                st.rerun()
                    
            except Exception as e:
                reply_text = f"[Error running orchestrator]: {e}"
                import traceback
                tb = traceback.format_exc()
                st.error(reply_text)
        
        else:
            lower = prompt.strip().lower()
            if lower in ("hi","hello","hey"):
                reply_text = "Hello! What would you like to learn today? Try: 'I want to learn fractions.'"
            elif "plan" in lower or "learn" in lower:
                reply_text = "I can create a plan for you. (Orchestrator isn't available — this is a fallback.)"
            else:
                reply_text = "I would normally route your input to the OrchestratorAgent, but it's not available. Try asking for a plan."

        # Add assistant response to CURRENT chat (if we didn't switch)
        st.session_state.chats[chat_key].append({"role": "assistant", "content": reply_text})
        if orch:
            orch.save_chat_history(chat_key, st.session_state.chats[chat_key])
            
        with st.chat_message("assistant"):
            st.markdown(reply_text)
        
        st.rerun()

