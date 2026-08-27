import streamlit as st
import datetime
import re
from api_client import SmartDocsAPIClient
from export_utils import (
    generate_ai_image,
    extract_and_render_plots,
    generate_pdf_export,
    generate_docx_export,
    generate_txt_export,
)

# ==========================================
# 1. PAGE CONFIG & AUTO-THEME ADAPTIVE STYLING
# ==========================================
st.set_page_config(
    page_title="SmartDocs AI",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* ─── Light Mode Variables (Default) ─── */
    :root {
        --app-title-grad: linear-gradient(90deg, #0284c7, #4f46e5);
        --app-sub-color: #64748b;
        --card-bg: #ffffff;
        --card-border: #e2e8f0;
        --card-text: #0f172a;
        --cite-bg: #f8fafc;
        --cite-border: #0284c7;
        --cite-text: #334155;
    }

    /* ─── Dark Mode Variables (Automatic Device Detection) ─── */
    @media (prefers-color-scheme: dark) {
        :root {
            --app-title-grad: linear-gradient(90deg, #38bdf8, #818cf8);
            --app-sub-color: #94a3b8;
            --card-bg: #1e293b;
            --card-border: #334155;
            --card-text: #f8fafc;
            --cite-bg: #0f172a;
            --cite-border: #38bdf8;
            --cite-text: #e2e8f0;
        }
    }

    /* Header styling */
    .app-header {
        padding-bottom: 1rem;
        border-bottom: 1px solid var(--card-border);
        margin-bottom: 1.5rem;
    }
    .app-title {
        font-size: 1.8rem;
        font-weight: 800;
        background: var(--app-title-grad);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.02em;
    }
    .app-subtitle {
        font-size: 0.9rem;
        color: var(--app-sub-color);
        margin-top: 0.2rem;
    }

    /* Auth Header Title */
    .auth-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: var(--app-title-grad);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.02em;
    }
    .auth-subtitle {
        font-size: 0.95rem;
        color: var(--app-sub-color);
        margin-top: 0.3rem;
    }

    /* Stat Cards */
    .stat-card {
        background: var(--card-bg);
        border: 1px solid var(--card-border);
        border-radius: 8px;
        padding: 1rem 1.2rem;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }
    .stat-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: var(--card-text);
    }
    .stat-label {
        font-size: 0.75rem;
        font-weight: 600;
        color: var(--app-sub-color);
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* Source Citation Cards */
    .citation-box {
        background-color: var(--cite-bg);
        border-left: 3px solid var(--cite-border);
        border-radius: 0 6px 6px 0;
        padding: 0.75rem 1rem;
        margin-top: 0.5rem;
        font-size: 0.85rem;
        color: var(--cite-text);
    }

    /* Badges */
    .badge {
        display: inline-block;
        padding: 0.2rem 0.5rem;
        font-size: 0.75rem;
        font-weight: 600;
        border-radius: 4px;
        background-color: var(--card-bg);
        border: 1px solid var(--card-border);
        color: var(--card-text);
        margin-right: 0.4rem;
    }
    .badge-primary {
        background-color: #0284c7;
        color: #ffffff;
        border: none;
    }
    .badge-success {
        background-color: #047857;
        color: #ffffff;
        border: none;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

api = SmartDocsAPIClient()

# ==========================================
# 2. SESSION STATE
# ==========================================
if "token" not in st.session_state:
    st.session_state.token = None
if "user" not in st.session_state:
    st.session_state.user = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "documents" not in st.session_state:
    st.session_state.documents = []


def refresh_documents(filename_filter=None):
    if st.session_state.token:
        res = api.list_documents(st.session_state.token, filename_filter)
        if res.status_code == 200:
            st.session_state.documents = res.json()


# ==========================================
# 3. AUTHENTICATION (LOGIN / SIGN UP)
# ==========================================
if not st.session_state.token:
    st.write("")
    col1, col2, col3 = st.columns([1, 1.6, 1])
    with col2:
        st.markdown(
            """
            <div style='text-align: center; margin-bottom: 1.8rem;'>
                <div class='auth-title'>SmartDocs AI</div>
                <div class='auth-subtitle'>Document Intelligence & AI Assistant Platform</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        with st.container(border=True):
            tab_login, tab_signup = st.tabs(["Sign In", "Create Account"])

            with tab_login:
                st.write("")
                login_email = st.text_input("Email", placeholder="name@company.com", key="auth_email")
                login_password = st.text_input("Password", type="password", placeholder="••••••••", key="auth_pw")

                if st.button("Sign In", use_container_width=True, type="primary"):
                    if not login_email or not login_password:
                        st.error("Please enter both email and password.")
                    else:
                        with st.spinner("Signing in..."):
                            res = api.login(login_email, login_password)
                            if res.status_code == 200:
                                data = res.json()
                                st.session_state.token = data["access_token"]
                                user_res = api.get_me(st.session_state.token)
                                if user_res.status_code == 200:
                                    st.session_state.user = user_res.json()
                                refresh_documents()
                                st.rerun()
                            else:
                                try:
                                    err_msg = res.json().get("detail", "Invalid credentials.")
                                except Exception:
                                    err_msg = "Invalid credentials."
                                st.error(err_msg)

            with tab_signup:
                st.write("")
                signup_name = st.text_input("Full Name", placeholder="Jane Doe", key="reg_name")
                signup_email = st.text_input("Email", placeholder="name@company.com", key="reg_email")
                signup_password = st.text_input("Password", type="password", placeholder="Min 8 characters", key="reg_pw")

                if st.button("Create Account", use_container_width=True):
                    if not signup_email or len(signup_password) < 8:
                        st.error("Please provide a valid email and minimum 8-character password.")
                    else:
                        with st.spinner("Creating account..."):
                            res = api.register(signup_email, signup_password, signup_name)
                            if res.status_code == 201:
                                st.success("Account created. You can now sign in.")
                            else:
                                try:
                                    err_msg = res.json().get("detail", "Registration failed.")
                                except Exception:
                                    err_msg = "Registration failed."
                                st.error(err_msg)

    st.stop()


# ==========================================
# 4. MAIN APP NAVIGATION
# ==========================================

with st.sidebar:
    st.markdown("<div style='font-size: 1.15rem; font-weight: 700;'>SmartDocs AI</div>", unsafe_allow_html=True)
    st.caption("AI Document Assistant")
    st.divider()

    user_name = st.session_state.user.get("full_name") or st.session_state.user.get("email")
    user_role = st.session_state.user.get("role", "user").upper()
    st.write(f"**{user_name}**")
    st.markdown(f"<span class='badge badge-primary'>{user_role}</span>", unsafe_allow_html=True)

    st.divider()
    nav_selection = st.radio(
        "Navigation",
        [
            "AI Assistant",
            "Knowledge Library",
            "Account Settings",
        ],
        index=0,
    )

    st.divider()
    health_res = api.health_check()
    status_label = "Online" if health_res.status_code == 200 else "Offline"
    st.caption(f"System Status: `{status_label}`")

    if st.button("Sign Out", use_container_width=True):
        st.session_state.token = None
        st.session_state.user = None
        st.session_state.messages = []
        st.session_state.documents = []
        st.session_state.current_scope_key = None
        st.rerun()


# ==========================================
# 1. AI ASSISTANT (CHAT, MULTI-MODAL & EXPORT)
# ==========================================
if nav_selection == "AI Assistant":
    st.markdown(
        """
        <div class='app-header'>
            <div class='app-title'>AI Document Assistant</div>
            <div class='app-subtitle'>Document Intelligence with Dynamic Math Graphs, AI Image Generation & 1-Click Exports</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    refresh_documents()
    doc_map = {"All Ingested Documents": None}
    for doc in st.session_state.documents:
        doc_map[f"{doc['filename']} ({doc['chunk_count']} chunks)"] = doc["id"]

    # Toolbar with In-Chat Quick Upload & Thread Controls
    with st.container(border=True):
        col_scope, col_quick_up, col_clear = st.columns([3, 2, 1])

        with col_scope:
            selected_label = st.selectbox(
                "Document Filter Scope:",
                options=list(doc_map.keys()),
                key="doc_scope_select",
            )
            selected_doc_id = doc_map[selected_label]
            scope_key = selected_doc_id if selected_doc_id else "all"

            # Auto-load thread history from MongoDB when document selection changes
            if "current_scope_key" not in st.session_state or st.session_state.current_scope_key != scope_key:
                st.session_state.current_scope_key = scope_key
                hist_res = api.get_thread_history(scope_key, st.session_state.token)
                if hist_res.status_code == 200:
                    st.session_state.messages = hist_res.json()
                else:
                    st.session_state.messages = []

        with col_quick_up:
            with st.popover("Upload Document to Chat", use_container_width=True):
                quick_file = st.file_uploader("Upload PDF, TXT, or DOCX", type=["pdf", "txt", "docx"], key="quick_up")
                if quick_file is not None:
                    if st.button("Process & Add to Chat", type="primary", use_container_width=True):
                        with st.spinner("Ingesting file into knowledge base..."):
                            up_res = api.upload_document(quick_file.read(), quick_file.name, st.session_state.token)
                            if up_res.status_code == 200:
                                st.success(f"Ingested '{quick_file.name}'! Ready to query.")
                                refresh_documents()
                                st.rerun()
                            else:
                                st.error("Upload failed.")

        with col_clear:
            st.write("")
            st.write("")
            if st.button("Clear Thread", use_container_width=True):
                api.clear_thread_history(scope_key, st.session_state.token)
                st.session_state.messages = []
                st.rerun()

    # Chat Stream
    if not st.session_state.messages:
        st.info("Ask questions, generate mathematical graphs, create AI image illustrations, or export answers to PDF, Word, and Text.")

    for idx, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            content = msg["content"]

            if msg["role"] == "assistant":
                # A. Detect and Render AI Image Generation Prompts
                img_prompt_match = re.search(r"\[IMAGE_PROMPT:\s*(.*?)\]", content)
                if img_prompt_match:
                    img_prompt = img_prompt_match.group(1)
                    with st.spinner("🎨 Generating AI artwork with diffusion model..."):
                        img_bytes = generate_ai_image(img_prompt)
                        if img_bytes:
                            st.image(img_bytes, caption=f"AI Generated Visual: {img_prompt}", use_container_width=True)
                            st.download_button(
                                label="📥 Download Generated Image (PNG)",
                                data=img_bytes,
                                file_name=f"SmartDocs_Image_{idx}.png",
                                mime="image/png",
                                key=f"dl_ai_img_{idx}",
                            )

                # B. Detect and Render Mathematical Graphs & Charts
                plot_images = extract_and_render_plots(content)
                for p_idx, p_bytes in enumerate(plot_images):
                    st.image(p_bytes, caption="Generated Visual Graph / Chart", use_container_width=True)
                    st.download_button(
                        label="📥 Download High-Res Graph (PNG)",
                        data=p_bytes,
                        file_name=f"SmartDocs_Plot_{idx}_{p_idx}.png",
                        mime="image/png",
                        key=f"dl_plot_{idx}_{p_idx}",
                    )

            # Display Cleaned Text & LaTeX Formulas
            display_text = re.sub(r"\[IMAGE_PROMPT:.*?\]", "", content).strip()
            st.markdown(display_text)

            if msg["role"] == "assistant":
                citations = msg.get("citations", [])

                # 1. Source Citations
                if citations:
                    with st.expander(f"Source Verification ({len(citations)} references)"):
                        for c in citations:
                            st.markdown(
                                f"<span class='badge badge-primary'>{c['filename']}</span> "
                                f"<span class='badge'>Chunk #{c['chunk_index']}</span> "
                                f"<span class='badge badge-success'>Score: {c['score']:.4f}</span>",
                                unsafe_allow_html=True,
                            )
                            st.markdown(f"<div class='citation-box'>\"{c['snippet']}\"</div>", unsafe_allow_html=True)
                            st.write("")

                # 2. One-Click Document Export Toolbar (PDF, DOCX, TXT)
                with st.expander("📥 Export & Download this Answer"):
                    c_pdf, c_docx, c_txt = st.columns(3)

                    user_q = st.session_state.messages[idx - 1]["content"] if idx > 0 else "Document Analysis"
                    pdf_bytes = generate_pdf_export(user_q, display_text, citations)
                    docx_bytes = generate_docx_export(user_q, display_text, citations)
                    txt_content = generate_txt_export(user_q, display_text, citations)

                    with c_pdf:
                        st.download_button(
                            label="📄 Export as PDF",
                            data=pdf_bytes,
                            file_name=f"SmartDocs_Report_{idx}.pdf",
                            mime="application/pdf",
                            key=f"exp_pdf_{idx}",
                            use_container_width=True,
                        )
                    with c_docx:
                        st.download_button(
                            label="📝 Export as Word (.docx)",
                            data=docx_bytes,
                            file_name=f"SmartDocs_Report_{idx}.docx",
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"exp_docx_{idx}",
                            use_container_width=True,
                        )
                    with c_txt:
                        st.download_button(
                            label="📋 Export as Text (.txt)",
                            data=txt_content.encode("utf-8"),
                            file_name=f"SmartDocs_Report_{idx}.txt",
                            mime="text/plain",
                            key=f"exp_txt_{idx}",
                            use_container_width=True,
                        )

    # Chat Input Box
    if user_prompt := st.chat_input("Type your question, graph request, or image prompt here..."):
        st.session_state.messages.append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing context & generating multi-modal response..."):
                history_to_send = st.session_state.messages[:-1]

                response = api.chat(
                    question=user_prompt,
                    token=st.session_state.token,
                    document_id=selected_doc_id,
                    chat_history=history_to_send,
                )
                if response.status_code == 200:
                    data = response.json()
                    answer_text = data["answer"]
                    citations = data.get("citations", [])

                    # Render AI Image if requested
                    img_prompt_match = re.search(r"\[IMAGE_PROMPT:\s*(.*?)\]", answer_text)
                    if img_prompt_match:
                        img_prompt = img_prompt_match.group(1)
                        img_bytes = generate_ai_image(img_prompt)
                        if img_bytes:
                            st.image(img_bytes, caption=f"AI Generated Visual: {img_prompt}", use_container_width=True)

                    # Render Math Plot if requested
                    plot_images = extract_and_render_plots(answer_text)
                    for p_bytes in plot_images:
                        st.image(p_bytes, caption="Generated Visual Graph / Chart", use_container_width=True)

                    display_text = re.sub(r"\[IMAGE_PROMPT:.*?\]", "", answer_text).strip()
                    st.markdown(display_text)

                    if citations:
                        with st.expander(f"Source Verification ({len(citations)} references)"):
                            for c in citations:
                                st.markdown(
                                    f"<span class='badge badge-primary'>{c['filename']}</span> "
                                    f"<span class='badge'>Chunk #{c['chunk_index']}</span> "
                                    f"<span class='badge badge-success'>Score: {c['score']:.4f}</span>",
                                    unsafe_allow_html=True,
                                )
                                st.markdown(f"<div class='citation-box'>\"{c['snippet']}\"</div>", unsafe_allow_html=True)
                                st.write("")

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": answer_text,
                            "citations": citations,
                        }
                    )
                    st.rerun()
                else:
                    try:
                        err = response.json().get("detail", response.text or "Error generating response.")
                    except Exception:
                        err = response.text or f"Server returned HTTP {response.status_code}"
                    st.error(f"Error: {err}")


# ==========================================
# 2. KNOWLEDGE LIBRARY (FILES & STORAGE)
# ==========================================
elif nav_selection == "Knowledge Library":
    st.markdown(
        """
        <div class='app-header'>
            <div class='app-title'>Knowledge Library & Storage</div>
            <div class='app-subtitle'>Manage uploaded files, inspect vector ingestion stats, and download from S3.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    refresh_documents()

    total_docs = len(st.session_state.documents)
    total_chunks = sum(d.get("chunk_count", 0) for d in st.session_state.documents)
    total_words = sum(d.get("word_count", 0) for d in st.session_state.documents)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"<div class='stat-card'><div class='stat-label'>Ingested Documents</div><div class='stat-value'>{total_docs}</div></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='stat-card'><div class='stat-label'>Total Vector Chunks</div><div class='stat-value'>{total_chunks}</div></div>", unsafe_allow_html=True)
    with c3:
        st.markdown(f"<div class='stat-card'><div class='stat-label'>Words Extracted</div><div class='stat-value'>{total_words:,}</div></div>", unsafe_allow_html=True)

    st.write("")

    with st.container(border=True):
        st.subheader("Upload Document")
        st.caption("Supported formats: PDF, DOCX, TXT. Uploaded files are parsed, stored in S3, and indexed in Qdrant.")

        file_to_upload = st.file_uploader("Upload file:", type=["pdf", "txt", "docx"], label_visibility="collapsed")
        if file_to_upload is not None:
            if st.button("Process and Ingest File", type="primary"):
                with st.spinner("Processing file, uploading to S3, and indexing vector chunks..."):
                    file_bytes = file_to_upload.read()
                    up_res = api.upload_document(file_bytes, file_to_upload.name, st.session_state.token)
                    if up_res.status_code == 200:
                        doc_data = up_res.json()
                        st.success(f"Ingested '{doc_data['filename']}' ({doc_data['chunk_count']} chunks indexed).")
                        refresh_documents()
                        st.rerun()
                    else:
                        st.error(f"Upload failed: {up_res.json().get('detail', 'Error')}")

    st.subheader("Document Library")
    if not st.session_state.documents:
        st.info("No documents uploaded yet.")
    else:
        for doc in st.session_state.documents:
            with st.container(border=True):
                col_meta, col_actions = st.columns([3, 1.2])
                with col_meta:
                    st.markdown(f"**{doc['filename']}**")
                    st.markdown(
                        f"<span class='badge'>{doc['file_type'].upper()}</span>"
                        f"<span class='badge'>{doc['size_bytes'] / 1024:.1f} KB</span>"
                        f"<span class='badge'>{doc['word_count']} words</span>"
                        f"<span class='badge badge-primary'>{doc['chunk_count']} chunks</span>"
                        f"<span class='badge'>Date: {doc['uploaded_at'][:10]}</span>",
                        unsafe_allow_html=True,
                    )
                with col_actions:
                    btn_c1, btn_c2 = st.columns(2)
                    with btn_c1:
                        dl_res = api.download_document(doc["id"], st.session_state.token)
                        if dl_res.status_code == 200:
                            st.download_button(
                                label="Download",
                                data=dl_res.content,
                                file_name=doc["filename"],
                                key=f"dl_{doc['id']}",
                                use_container_width=True,
                            )
                    with btn_c2:
                        if st.button("Delete", key=f"del_{doc['id']}", use_container_width=True):
                            with st.spinner("Deleting document and vector records..."):
                                del_res = api.delete_document(doc["id"], st.session_state.token)
                                if del_res.status_code == 200:
                                    st.success("Document deleted.")
                                    refresh_documents()
                                    st.rerun()
                                else:
                                    st.error("Failed to delete.")


# ==========================================
# 3. ACCOUNT SETTINGS & ADMINISTRATION
# ==========================================
elif nav_selection == "Account Settings":
    st.markdown(
        """
        <div class='app-header'>
            <div class='app-title'>Account & Administration</div>
            <div class='app-subtitle'>Manage profile details and view system registry.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_acc, col_upd = st.columns(2)
    with col_acc:
        with st.container(border=True):
            st.subheader("Profile Information")
            st.write(f"**Email:** `{st.session_state.user.get('email')}`")
            st.write(f"**Full Name:** {st.session_state.user.get('full_name') or 'Not specified'}")
            st.write(f"**Role:** `{st.session_state.user.get('role', 'user').upper()}`")
            st.write(f"**User ID:** `{st.session_state.user.get('id')}`")

    with col_upd:
        with st.container(border=True):
            st.subheader("Update Name")
            new_name = st.text_input("Full Name:", value=st.session_state.user.get("full_name") or "")
            if st.button("Save Changes"):
                with st.spinner("Updating name..."):
                    up_res = api.update_me(new_name, st.session_state.token)
                    if up_res.status_code == 200:
                        st.session_state.user = up_res.json()
                        st.success("Profile updated.")
                        st.rerun()
                    else:
                        st.error("Failed to update.")

    # Admin Panel (Only visible for admin accounts)
    if st.session_state.user.get("role") == "admin":
        st.divider()
        st.subheader("User Registry (Admin Access)")
        st.caption("Manage registered platform users and permission levels.")

        users_res = api.list_all_users(st.session_state.token)
        if users_res.status_code == 200:
            users_list = users_res.json()
            my_id = st.session_state.user.get("id")

            for u in users_list:
                with st.container(border=True):
                    col_uinfo, col_urole, col_uaction = st.columns([3, 1.2, 1.2])

                    with col_uinfo:
                        st.markdown(f"**{u['email']}**")
                        st.caption(f"Name: {u.get('full_name') or 'Not set'} | ID: `{u['id']}`")

                    with col_urole:
                        role_badge_class = "badge-primary" if u["role"] == "admin" else "badge"
                        st.markdown(f"<span class='badge {role_badge_class}'>{u['role'].upper()}</span>", unsafe_allow_html=True)

                    with col_uaction:
                        if u["role"] == "user":
                            if st.button("Promote to Admin", key=f"role_btn_{u['id']}", type="primary", use_container_width=True):
                                with st.spinner("Updating role..."):
                                    up_res = api.update_user_role(u["id"], "admin", st.session_state.token)
                                    if up_res.status_code == 200:
                                        st.rerun()
                                    else:
                                        st.error("Failed to update role.")

                        elif u["role"] == "admin" and u["id"] > my_id:
                            if st.button("Demote to User", key=f"role_btn_{u['id']}", type="secondary", use_container_width=True):
                                with st.spinner("Updating role..."):
                                    up_res = api.update_user_role(u["id"], "user", st.session_state.token)
                                    if up_res.status_code == 200:
                                        st.rerun()
                                    else:
                                        st.error("Failed to update role.")

                        else:
                            st.write("")
        else:
            st.warning("Could not load user list.")