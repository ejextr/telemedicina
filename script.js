const API_BASE = window.location.origin;

const state = {
    token: (() => {
        try {
            let token = sessionStorage.getItem("medicappToken");
            if (token) {
                return token;
            }
            return null;
        } catch (e) {
            console.warn("Storage not available:", e);
            return null;
        }
    })(),
    refreshToken: (() => {
        try {
            let token = localStorage.getItem("medicappRefreshToken");
            if (token) {
                return token;
            }
            // Fallback to sessionStorage
            token = sessionStorage.getItem("medicappRefreshToken");
            if (token) {
                return token;
            }
            return null;
        } catch (e) {
            console.warn("Storage not available:", e);
            return null;
        }
    })(),
    user: null,
    doctors: [],
    doctorStatus: null,
    patientRooms: [],
    doctorRooms: [],
    currentRoom: null,
    pollHandle: null,
    invitedRoomId: null,
};

const screens = {
    login: document.getElementById("login-screen"),
    register: document.getElementById("register-screen"),
    dashboard: document.getElementById("dashboard"),
};

// Lazy loading of DOM elements to avoid null references
const elementCache = {};
const elements = new Proxy({}, {
    get(target, prop) {
        if (!elementCache[prop]) {
            // Map property names to selectors
            const selectors = {
                loginForm: "#login-form",
                registerBtn: "#register-btn",
                registerForm: "#register-form",
                backToLogin: "#back-to-login",
                forgotLink: ".forgot-link",
                menuToggle: "#menu-toggle",
                overlay: "#overlay",
                patientMenuOverlay: "#patient-menu-overlay",
                patientMenuItems: ".menu-item",
                patientDashboard: "#patient-dashboard",
                patientAvatar: "#patient-avatar",
                avatarPlaceholder: "#avatar-placeholder",
                miaChatModal: "#mia-chat-modal",
                closeMiaChat: "#close-mia-chat",
                miaChatMessages: "#mia-chat-messages",
                miaChatInput: "#mia-chat-input",
                sendMiaMessage: "#send-mia-message",
                guardiaContent: "#guardia-content",
                doctorsOnDuty: "#doctors-on-duty",
                exitGuardia: "#exit-guardia",
                searchToggle: "#search-toggle",
                searchForm: "#search-form",
                personaToggle: "#persona-toggle",
                personaButtons: ".persona-btn",
                userName: "#user-name",
                profileName: "#profile-name",
                profileRole: "#profile-role",
                logoutBtn: "#logout-btn",
                profileForm: "#profile-form",
                specialty: "#specialty",
                experience_years: "#experience_years",
                birth_date: "#birth_date",
                medical_history: "#medical_history",
                allergies: "#allergies",
                avatar: "#avatar",
                doctorFields: "#doctor-fields",
                patientFields: "#patient-fields",
                videoModal: "#video-modal",
                closeVideo: "#close-video",
                callInviteModal: "#call-invite-modal",
                rejectCall: "#reject-call",
                acceptCall: "#accept-call",
                doctorList: "#doctor-list",
                selectedDoctorCard: "#selected-doctor-card",
                selectedDoctorName: "#selected-doctor-name",
                selectedDoctorStatus: "#selected-doctor-status",
                requestGuardForm: "#request-guard-form",
                guardNote: "#guard-note",
                patientRoomCard: "#patient-room-card",
                patientRoomInfo: "#room-info",
                openRoomChat: "#open-room-chat",
                toggleGuard: "#toggle-guard",
                toggleAppointments: "#toggle-appointments",
                doctorRooms: "#doctor-rooms",
                refreshDoctorRooms: "#refresh-doctor-rooms",
                patientRooms: "#patient-rooms",
                refreshPatientRooms: "#refresh-patient-rooms",
                threadList: "#thread-list",
                chatPanel: "#chat-panel",
                chatTitle: "#chat-title",
                chatMessages: "#chat-messages",
                chatForm: "#chat-form",
                chatInput: "#chat-input",
                closeChat: "#close-chat",
                guardiaView: "#guardia-view",
                guardiaSummary: "#guardia-room-summary",
                guardiaChat: "#guardia-chat",
                guardiaChatForm: "#guardia-chat-form",
                guardiaChatInput: "#guardia-chat-input",
                emergencyButton: "#emergency-button",
                emergencyModal: "#emergency-modal",
                callEmergency: "#call-emergency",
                confirmEmergency: "#confirm-emergency",
                cancelEmergency: "#cancel-emergency"
            };
            const selector = selectors[prop];
            if (selector) {
                // Use querySelectorAll only for known multiple elements
                const multipleSelectors = ['.menu-item', '.persona-btn'];
                if (multipleSelectors.includes(selector)) {
                    elementCache[prop] = document.querySelectorAll(selector);
                } else {
                    elementCache[prop] = document.querySelector(selector);
                }
            } else {
                elementCache[prop] = null;
            }
        }
        return elementCache[prop];
    }
});

const sidebarItems = Array.from(document.querySelectorAll(".sidebar-menu li[data-target]"));

function showScreen(target) {
    Object.values(screens).forEach((screen) => {
        const isTarget = screen === target;
        screen.classList.toggle("active", isTarget);
        if (!isTarget) {
            screen.setAttribute("hidden", "true");
        } else {
            screen.removeAttribute("hidden");
        }
    });
}

function showDashboardView(viewId) {
    document.querySelectorAll(".app-view").forEach((view) => {
        if (view.id === viewId) {
            view.removeAttribute("hidden");
        } else {
            view.setAttribute("hidden", "true");
        }
    });
    sidebarItems.forEach((item) => {
        item.classList.toggle("active", item.dataset.target === viewId);
    });
    if (viewId === "profile-view") {
        loadProfile();
    }
}

async function refreshToken() {
    try {
        const response = await fetch(`${API_BASE}/auth/refresh`, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${state.token}`,
                "Content-Type": "application/json"
            }
        });
        if (response.ok) {
            const data = await response.json();
            setToken(data.access_token);
            return true;
        }
    } catch (error) {
        console.error("Error refreshing token:", error);
    }
    return false;
}

async function apiFetch(path, options = {}) {
    const headers = options.headers ? { ...options.headers } : {};
    if (state.token) {
        headers["Authorization"] = `Bearer ${state.token}`;
    }
    console.log(`[client] apiFetch ${path} - sending headers:`, headers);
    const isForm = options.body instanceof FormData;
    if (!isForm && options.method && options.method !== "GET" && !headers["Content-Type"]) {
        headers["Content-Type"] = "application/json";
    }
    try {
        const response = await fetch(`${API_BASE}${path}`, { ...options, headers });

        if (!response.ok) {
            // Handle 401 Unauthorized - only clear token for login/register endpoints
            if (response.status === 401 && (path.includes('/auth/login') || path.includes('/auth/register'))) {
                console.warn("Credenciales inválidas en login/register");
                setToken(null);
                throw new Error("Credenciales inválidas");
            }
            // For other 401s, try to refresh token first (but not for refresh endpoint)
            if (response.status === 401 && !path.includes('/auth/refresh')) {
                console.warn(`Token expirado para endpoint: ${path}, intentando refresh`);
                const refreshed = await refreshToken();
                if (refreshed) {
                    // Retry the request with new token
                    return apiFetch(path, options);
                } else {
                    console.warn("No se pudo refrescar el token, limpiando sesión");
                    setToken(null);
                    state.user = null;
                    showScreen(screens.login);
                    throw new Error("Sesión expirada. Has sido redirigido al login.");
                }
            } else if (response.status === 401) {
                // For refresh endpoint or if refresh failed
                console.warn(`Token inválido para endpoint: ${path}, limpiando sesión`);
                setToken(null);
                state.user = null;
                showScreen(screens.login);
                throw new Error("Sesión expirada. Has sido redirigido al login.");
            }

            let detail = "Error inesperado";
            try {
                const problem = await response.json();
                if (problem?.detail) {
                    detail = Array.isArray(problem.detail) ? problem.detail[0].msg : problem.detail;
                }
            } catch (_) {
                // ignore JSON parse errors
            }
            throw new Error(detail);
        }
        if (response.status === 204) return null;
        const contentType = response.headers.get("content-type");
        if (contentType && contentType.includes("application/json")) {
            const data = await response.json();
            console.log(`API response for ${path}:`, data);
            return data;
        }
        const text = await response.text();
        console.log(`API response for ${path}:`, text);
        return text;
    } catch (error) {
        console.error(`Request failed for ${path}:`, error);
        throw error;
    }
}

function setToken(token) {
    state.token = token;
    try {
        if (token) {
            sessionStorage.setItem("medicappToken", token);
        } else {
            sessionStorage.removeItem("medicappToken");
        }
    } catch (e) {
        console.error("Failed to access sessionStorage:", e);
    }
}

function setRefreshToken(token) {
    state.refreshToken = token;
    try {
        if (token) {
            localStorage.setItem("medicappRefreshToken", token);
        } else {
            localStorage.removeItem("medicappRefreshToken");
        }
    } catch (e) {
        console.error("Failed to access localStorage:", e);
        // Fallback: try sessionStorage
        try {
            if (token) {
                sessionStorage.setItem("medicappRefreshToken", token);
            } else {
                sessionStorage.removeItem("medicappRefreshToken");
            }
        } catch (e2) {
            console.error("Failed to access sessionStorage too:", e2);
        }
    }
}

async function handleLogin(event) {
    event.preventDefault();
    const form = new FormData(elements.loginForm);
    const email = form.get("email");
    const password = form.get("password");
    try {
        const token = await apiFetch("/auth/login", {
            method: "POST",
            body: JSON.stringify({ email, password }),
        });
        setToken(token.access_token);
        console.log("[client] handleLogin: stored token in sessionStorage:", sessionStorage.getItem("medicappToken"));
        // Debug: ask server what it receives
        try {
            const echo = await apiFetch("/debug/echo-auth");
            console.log("[client] debug echo-auth:", echo);
        } catch (e) {
            console.warn("[client] debug echo-auth failed:", e);
        }
        state.user = await apiFetch("/users/me");
        await onAuthReady();
    } catch (error) {
        alert(error.message);
    }
}

async function handleRegister(event) {
    event.preventDefault();
    const role = document.querySelector('input[name="user-role"]:checked')?.value || "patient";
    const name = document.getElementById("signup-name").value.trim();
    const email = document.getElementById("signup-email").value.trim();
    const password = document.getElementById("signup-password").value;
    const confirm = document.getElementById("signup-confirm").value;
    if (password !== confirm) {
        alert("Las contrasenas no coinciden");
        return;
    }
    if (password.length < 8) {
        alert("La contrasena debe tener al menos 8 caracteres");
        return;
    }
    try {
        await apiFetch("/auth/register", {
            method: "POST",
            body: JSON.stringify({ name, email, password, role }),
        });
        alert("Cuenta creada. Ahora podes iniciar sesion.");
        showScreen(screens.login);
        elements.loginForm.reset();
        elements.loginForm.querySelector(`input[name="login-role"][value="${role}"]`).checked = true;
    } catch (error) {
        alert(error.message);
    }
}

async function onAuthReady() {
    showScreen(screens.dashboard);
    document.body.classList.add("dashboard-active", "logged-in");
    applyRoleUI();
    await loadInitialData();
    showDashboardView(state.user.role === "doctor" ? "doctor-view" : "patient-view");
}

function applyRoleUI() {
    const role = state.user?.role || "patient";
    if (elements.userName) elements.userName.textContent = state.user?.name || "";
    if (elements.profileName) elements.profileName.textContent = state.user?.name || "";
    if (elements.profileRole) elements.profileRole.textContent = role === "doctor" ? "Medico" : "Paciente";
    document.body.classList.toggle("role-doctor", role === "doctor");
    if (elements.personaToggle) elements.personaToggle.toggleAttribute("hidden", role !== "doctor");
    sidebarItems.forEach((item) => {
        if (item.dataset.roleOnly === "doctor") {
            item.toggleAttribute("hidden", role !== "doctor");
        }
    });
    if (elements.personaButtons) elements.personaButtons.forEach((btn) => {
        btn.classList.toggle("active", role === "doctor" && btn.dataset.mode === "doctor");
    });
}

async function loadInitialData() {
    const role = state.user?.role;
    try {
        if (role === "doctor") {
            await Promise.all([loadDoctorStatus(), loadDoctorRooms(), loadDoctors()]);
        } else {
            await Promise.all([loadDoctors(), loadPatientRooms()]);
        }
        buildThreadList();
    } catch (error) {
        console.error("Error loading initial data:", error);
        // Don't throw here, just log - the UI should still work even if some data fails to load
    }
}

async function loadDoctors() {
    try {
        state.doctors = await apiFetch("/doctors");
        renderDoctorList(state.doctors);
    } catch (error) {
        console.error(error);
    }
}

async function loadDoctorStatus() {
    try {
        state.doctorStatus = await apiFetch("/doctor/status");
        updateDoctorStatusUI();
    } catch (error) {
        console.error(error);
    }
}

async function loadPatientRooms() {
    try {
        state.patientRooms = await apiFetch("/patient/waiting-rooms");
        renderPatientRooms();
        buildThreadList();
        // Check for call invites
        if (state.patientRooms && Array.isArray(state.patientRooms)) {
            const invitedRoom = state.patientRooms.find(r => r.call_status === "invited");
            if (invitedRoom) {
                showCallInvite(invitedRoom.id);
            }
        }
    } catch (error) {
        console.error(error);
    }
}

async function loadDoctorRooms() {
    try {
        state.doctorRooms = await apiFetch("/doctor/waiting-rooms");
        renderDoctorRooms();
        buildThreadList();
    } catch (error) {
        console.error(error);
    }
}

function renderDoctorList(doctors) {
    if (!elements.doctorsOnDuty) return; // Element not found
    if (!doctors.length) {
        elements.doctorsOnDuty.classList.add("empty");
        elements.doctorsOnDuty.innerHTML = '<p class="empty-copy">No hay profesionales para mostrar aun.</p>';
        return;
    }
    elements.doctorsOnDuty.classList.remove("empty");
    elements.doctorsOnDuty.innerHTML = "";
    doctors.forEach((doctor) => {
        const item = document.createElement("div");
        item.className = "doctor-item";
        item.innerHTML = `
            <header>
                <strong>${doctor.name}</strong>
                <span class="status-pill ${doctor.is_on_guard ? "" : "off"}">
                    ${doctor.is_on_guard ? "Guardia disponible" : "Fuera de guardia"}
                </span>
                <span class="status-pill ${doctor.is_accepting ? "" : "off"}">
                    ${doctor.is_accepting ? "Turnos abiertos" : "Sin turnos"}
                </span>
            </header>
            <button class="ghost-button ghost-sm" data-action="select-doctor" data-id="${doctor.id}">Ver detalle</button>
        `;
        elements.doctorsOnDuty.appendChild(item);
    });
}

function renderPatientRooms() {
    const container = elements.patientRooms;
    if (!container) return; // Element not found
    if (!state.patientRooms.length) {
        container.classList.add("empty");
        container.innerHTML = '<p class="empty-copy">Todavia no generaste una sala.</p>';
        if (elements.patientRoomCard) elements.patientRoomCard.setAttribute("hidden", "true");
        return;
    }
    container.classList.remove("empty");
    container.innerHTML = "";
    state.patientRooms.forEach((room) => {
        const doctorName = room.doctor_name || "Medico";
        const item = document.createElement("div");
        item.className = "waiting-card";
        item.innerHTML = `
            <header>
                <div>
                    <strong>${doctorName}</strong>
                    <p>Estado: ${room.status}</p>
                </div>
                <button class="ghost-button ghost-sm" data-action="open-room" data-room="${room.id}">Abrir chat</button>
            </header>
            <p>${room.note || "Sin comentarios"}</p>
        `;
        container.appendChild(item);
    });
    const first = state.patientRooms[0];
    if (elements.patientRoomCard) elements.patientRoomCard.removeAttribute("hidden");
    if (elements.patientRoomInfo) elements.patientRoomInfo.textContent = `${first.doctor_name} - Estado: ${first.status}`;
    if (elements.openRoomChat) elements.openRoomChat.dataset.room = first.id;
}

function renderDoctorRooms() {
    const container = elements.doctorRooms;
    if (!state.doctorRooms.length) {
        container.classList.add("empty");
        container.innerHTML = '<p class="empty-copy">No hay pacientes esperando.</p>';
        return;
    }
    container.classList.remove("empty");
    container.innerHTML = "";
    state.doctorRooms.forEach((room) => {
        const patientName = room.patient_name || "Paciente";
        const item = document.createElement("div");
        item.className = "waiting-card";
        item.innerHTML = `
            <header>
                <div>
                    <strong>${patientName}</strong>
                    <p>Estado: ${room.status} | Llamada: ${room.call_status}</p>
                </div>
                <div style="display: flex; gap: 8px;">
                    <button class="ghost-button ghost-sm" data-action="open-room" data-room="${room.id}">Abrir sala</button>
                    ${room.call_status === "none" ? `<button class="primary-button ghost-sm" data-action="start-call" data-room="${room.id}">Hacer pasar</button>` : ""}
                </div>
            </header>
            <p>${room.note || "Sin comentarios"}</p>
        `;
        container.appendChild(item);
    });
}

function updateDoctorStatusUI() {
    if (!state.doctorStatus) return;
    elements.toggleGuard.textContent = state.doctorStatus.is_on_guard ? "Apagar guardia" : "Encender guardia";
    elements.toggleAppointments.textContent = state.doctorStatus.is_accepting ? "Cerrar turnos" : "Abrir turnos";
}

function selectDoctor(doctorId) {
    const doctor = state.doctors.find((d) => d.id === Number(doctorId));
    if (!doctor) return;
    elements.selectedDoctorCard.removeAttribute("hidden");
    elements.selectedDoctorName.textContent = doctor.name;
    const guardText = doctor.is_on_guard ? "Guardia disponible" : "Fuera de guardia";
    const turnosText = doctor.is_accepting ? "Turnos abiertos" : "Sin turnos";
    elements.selectedDoctorStatus.textContent = `${guardText} - ${turnosText}`;
    elements.selectedDoctorStatus.className = `status-pill ${doctor.is_on_guard ? "" : "off"}`;
    elements.requestGuardForm.dataset.doctorId = doctor.id;
}

async function requestGuard(event) {
    event.preventDefault();
    const doctorId = Number(elements.requestGuardForm.dataset.doctorId);
    if (!doctorId) return;
    const note = elements.guardNote.value.trim();
    try {
        const room = await apiFetch("/waiting-room", {
            method: "POST",
            body: JSON.stringify({ doctor_id: doctorId, note }),
        });
        elements.guardNote.value = "";
        elements.selectedDoctorCard.setAttribute("hidden", "true");
        await loadPatientRooms();
        openRoom(room);
        alert("Te agregamos a la sala de espera. Un profesional te contactara.");
    } catch (error) {
        alert(error.message);
    }
}

function roomParticipantName(userId, room) {
    if (userId === room.patient_id) {
        return room.patient_name || "Paciente";
    }
    if (userId === room.doctor_id) {
        return room.doctor_name || "Medico";
    }
    return "Participante";
}

function renderMessages(messages) {
    if (!state.currentRoom) return;
    elements.chatMessages.innerHTML = "";
    elements.guardiaChat.innerHTML = "";
    messages.forEach((msg) => {
        const isMe = msg.sender_id === state.user.id;
        const bubble = document.createElement("div");
        bubble.className = `message-bubble ${isMe ? "me" : "them"}`;
        bubble.innerHTML = `
            <span>${roomParticipantName(msg.sender_id, state.currentRoom)}</span>
            <p>${msg.content}</p>
            <span class="message-meta">${new Date(msg.created_at).toLocaleString()}</span>
        `;
        const clone = bubble.cloneNode(true);
        elements.chatMessages.appendChild(bubble);
        elements.guardiaChat.appendChild(clone);
    });
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
    elements.guardiaChat.scrollTop = elements.guardiaChat.scrollHeight;
}

async function fetchMessages(roomId) {
    try {
        const messages = await apiFetch(`/waiting-room/${roomId}/messages`);
        renderMessages(messages);
    } catch (error) {
        console.error(error);
    }
}

function openRoom(room) {
    state.currentRoom = room;
    buildThreadList();
    elements.chatPanel.removeAttribute("hidden");
    elements.guardiaView.removeAttribute("hidden");
    elements.chatTitle.textContent = state.user.role === "doctor" ? room.patient_name : room.doctor_name;
    elements.guardiaSummary.innerHTML = `
        <p><strong>Medico:</strong> ${room.doctor_name}</p>
        <p><strong>Paciente:</strong> ${room.patient_name}</p>
        <p><strong>Estado:</strong> ${room.status}</p>
        <p><strong>Nota:</strong> ${room.note || "Sin comentarios"}</p>
    `;
    showDashboardView("messages-view");
    fetchMessages(room.id);
    startPolling(room.id);
}

function buildThreadList() {
    const role = state.user?.role;
    const rooms = role === "doctor" ? state.doctorRooms : state.patientRooms;
    elements.threadList.innerHTML = "";
    if (!rooms.length) {
        elements.threadList.innerHTML = '<p class="empty-copy">Sin conversaciones activas.</p>';
        return;
    }
    rooms.forEach((room) => {
        const item = document.createElement("div");
        item.className = "thread-item";
        if (state.currentRoom && state.currentRoom.id === room.id) {
            item.classList.add("active");
        }
        const partner = role === "doctor" ? room.patient_name : room.doctor_name;
        item.innerHTML = `
            <strong>${partner}</strong>
            <span>${room.status}</span>
        `;
        item.dataset.room = room.id;
        elements.threadList.appendChild(item);
    });
}

function startPolling(roomId) {
    stopPolling();
    state.pollHandle = setInterval(async () => {
        await fetchMessages(roomId);
        if (state.user.role === "doctor") {
            await loadDoctorRooms();
        } else {
            await loadPatientRooms();
        }
    }, 4000);
}

function stopPolling() {
    if (state.pollHandle) {
        clearInterval(state.pollHandle);
        state.pollHandle = null;
    }
}

async function sendChatMessage(event) {
    event.preventDefault();
    if (!state.currentRoom) return;
    const input = event.target === elements.chatForm ? elements.chatInput : elements.guardiaChatInput;
    const content = input.value.trim();
    if (!content) return;
    try {
        await apiFetch(`/waiting-room/${state.currentRoom.id}/messages`, {
            method: "POST",
            body: JSON.stringify({ content }),
        });
        input.value = "";
        await fetchMessages(state.currentRoom.id);
        if (state.user.role === "doctor") {
            await loadDoctorRooms();
        } else {
            await loadPatientRooms();
        }
        buildThreadList();
    } catch (error) {
        alert(error.message);
    }
}

function resetSelection() {
    stopPolling();
    state.currentRoom = null;
    elements.chatPanel.setAttribute("hidden", "true");
    elements.guardiaView.setAttribute("hidden", "true");
}

function handleThreadClick(event) {
    const item = event.target.closest(".thread-item");
    if (!item) return;
    const roomId = Number(item.dataset.room);
    const role = state.user?.role;
    const rooms = role === "doctor" ? state.doctorRooms : state.patientRooms;
    const room = rooms.find((r) => r.id === roomId);
    if (room) {
        openRoom(room);
    }
}

async function toggleAvailability(field) {
    if (!state.doctorStatus) await loadDoctorStatus();
    const payload = {
        is_on_guard: state.doctorStatus.is_on_guard,
        is_accepting: state.doctorStatus.is_accepting,
    };
    payload[field] = !payload[field];
    try {
        state.doctorStatus = await apiFetch("/doctor/status", {
            method: "POST",
            body: JSON.stringify(payload),
        });
        updateDoctorStatusUI();
        await Promise.all([loadDoctors(), loadDoctorRooms()]);
        buildThreadList();
    } catch (error) {
        console.error("Error in toggle", error);
        alert(error.message);
    }
}

function handleSidebarClick(event) {
    const item = event.target.closest("li[data-target]");
    if (!item) return;
    const roleOnly = item.dataset.roleOnly;
    if (roleOnly === "doctor" && state.user?.role !== "doctor") return;
    showDashboardView(item.dataset.target);
}

function handlePatientMenuClick(event) {
    const action = event.target.dataset.action;
    elements.patientMenuOverlay.hidden = true;
    switch (action) {
        case "guardia":
            showDashboardView("guardia-view");
            break;
        case "turnos":
            alert("Turnos: Próximamente disponible");
            break;
        case "historial":
            alert("Historial médico: Próximamente disponible");
            break;
        case "mensajes":
            showDashboardView("messages-view");
            break;
        case "perfil":
            showDashboardView("profile-view");
            break;
        default:
            break;
    }
}

async function loadProfile() {
    try {
        const profile = await apiFetch("/users/me/profile");
        elements.specialty.value = profile.specialty || "";
        elements.experience_years.value = profile.experience_years || "";
        elements.birth_date.value = profile.birth_date ? profile.birth_date.split("T")[0] : "";
        elements.medical_history.value = profile.medical_history || "";
        elements.allergies.value = profile.allergies || "";
        elements.avatar.value = profile.avatar || "";
        if (profile.avatar) {
            elements.patientAvatar.src = profile.avatar;
            elements.patientAvatar.style.display = "block";
            elements.avatarPlaceholder.style.display = "none";
        } else {
            elements.patientAvatar.style.display = "none";
            elements.avatarPlaceholder.style.display = "block";
        }
        const role = state.user.role;
        elements.doctorFields.toggleAttribute("hidden", role !== "doctor");
        elements.patientFields.toggleAttribute("hidden", role !== "patient");
    } catch (error) {
        alert("Error cargando perfil: " + error.message);
    }
}

async function saveProfile(event) {
    event.preventDefault();
    const data = {};
    if (state.user.role === "doctor") {
        data.specialty = elements.specialty.value.trim();
        data.experience_years = elements.experience_years.value ? Number(elements.experience_years.value) : null;
    } else {
        data.birth_date = elements.birth_date.value || null;
        data.medical_history = elements.medical_history.value.trim();
        data.allergies = elements.allergies.value.trim();
    }
    data.avatar = elements.avatar.value.trim() || null;
    try {
        await apiFetch("/users/me/profile", {
            method: "PUT",
            body: JSON.stringify(data),
        });
        alert("Perfil actualizado.");
        showScreen(screens.dashboard);
    } catch (error) {
        alert("Error guardando perfil: " + error.message);
    }
}

function clearState() {
    stopPolling();
    setToken(null);
    state.user = null;
    state.doctors = [];
    state.doctorStatus = null;
    state.patientRooms = [];
    state.doctorRooms = [];
    state.currentRoom = null;
    document.body.classList.remove("dashboard-active", "logged-in", "role-doctor", "menu-open");
    resetSelection();
    showScreen(screens.login);
}

function initEventListeners() {
    try {
        if (elements.loginForm) elements.loginForm.addEventListener("submit", handleLogin);
        if (elements.registerBtn) elements.registerBtn.addEventListener("click", () => {
            showScreen(screens.register);
            if (elements.registerForm) elements.registerForm.reset();
            const terms = document.getElementById("signup-terms");
            if (terms) terms.checked = false;
        });
        if (elements.registerForm) elements.registerForm.addEventListener("submit", handleRegister);
        if (elements.backToLogin) elements.backToLogin.addEventListener("click", () => showScreen(screens.login));
        if (elements.forgotLink) {
            elements.forgotLink.addEventListener("click", (event) => {
                event.preventDefault();
                alert("Prototipo: te enviariamos un enlace para recuperar la contrasena.");
            });
        }
    } catch (e) {
        console.warn("Error in initEventListeners part 1:", e);
    }
    try {
        if (elements.menuToggle) elements.menuToggle.addEventListener("click", () => {
            if (document.body.classList.contains("role-doctor")) {
                document.body.classList.toggle("menu-open");
            } else {
                if (elements.patientMenuOverlay) elements.patientMenuOverlay.hidden = !elements.patientMenuOverlay.hidden;
            }
        });
        if (elements.overlay) elements.overlay.addEventListener("click", () => document.body.classList.remove("menu-open"));
        if (elements.patientMenuOverlay) elements.patientMenuOverlay.addEventListener("click", (event) => {
            if (event.target === elements.patientMenuOverlay) {
                elements.patientMenuOverlay.hidden = true;
            }
        });
        if (elements.patientMenuItems) elements.patientMenuItems.forEach((item) => item.addEventListener("click", handlePatientMenuClick));
    } catch (e) {
        console.warn("Error in initEventListeners part 2:", e);
    }
    try {
        if (elements.patientDashboard) elements.patientDashboard.addEventListener("click", (event) => {
            if (event.target.matches('.action-btn[data-action]')) {
                const action = event.target.dataset.action;
                switch (action) {
                    case "guardia":
                        showDashboardView("guardia-view");
                        if (elements.miaChatModal) elements.miaChatModal.style.display = "flex";
                        if (elements.guardiaContent) elements.guardiaContent.hidden = true;
                        break;
                    case "turnos":
                        alert("Turnos: Próximamente disponible");
                        break;
                    case "historial":
                        alert("Historial médico: Próximamente disponible");
                        break;
                    case "mensajes":
                        showDashboardView("messages-view");
                        break;
                    case "perfil":
                        showDashboardView("profile-view");
                        break;
                    default:
                        break;
                }
            }
        });
        if (elements.closeMiaChat) elements.closeMiaChat.addEventListener("click", () => {
            if (elements.miaChatModal) elements.miaChatModal.style.display = "none";
            if (elements.guardiaContent) elements.guardiaContent.hidden = false;
            loadDoctorsOnDuty();
        });
        if (elements.sendMiaMessage) elements.sendMiaMessage.addEventListener("click", sendMiaMessage);
        if (elements.miaChatInput) elements.miaChatInput.addEventListener("keypress", (event) => {
            if (event.key === "Enter") {
                sendMiaMessage();
            }
        });
        if (elements.exitGuardia) elements.exitGuardia.addEventListener("click", () => showDashboardView("patient-view"));
        if (elements.doctorsOnDuty) elements.doctorsOnDuty.addEventListener("click", (event) => {
            if (event.target.matches('[data-action="view-profile"]')) {
                const doctorId = event.target.dataset.doctorId;
                viewDoctorProfile(doctorId);
            } else if (event.target.matches('[data-action="join-waiting-room"]')) {
                const doctorId = event.target.dataset.doctorId;
                joinWaitingRoom(doctorId);
            }
        });
    } catch (e) {
        console.warn("Error in initEventListeners part 3:", e);
    }
    try {
        if (elements.searchToggle) elements.searchToggle.addEventListener("click", () => document.body.classList.toggle("search-open"));
        sidebarItems.forEach((item) => item.addEventListener("click", handleSidebarClick));
        if (elements.logoutBtn) elements.logoutBtn.addEventListener("click", clearState);
        if (elements.searchForm) elements.searchForm.addEventListener("submit", handleSearch);
        if (elements.doctorsOnDuty) {
            elements.doctorsOnDuty.addEventListener("click", (event) => {
                if (event.target.matches('[data-action="select-doctor"]')) {
                    selectDoctor(event.target.dataset.id);
                }
            });
        }
        if (elements.requestGuardForm) elements.requestGuardForm.addEventListener("submit", requestGuard);
        if (elements.patientRooms) elements.patientRooms.addEventListener("click", (event) => {
            if (event.target.matches('[data-action="open-room"]')) {
                const roomId = Number(event.target.dataset.room);
                const room = state.patientRooms.find((r) => r.id === roomId);
                if (room) openRoom(room);
            }
        });
        if (elements.doctorRooms) elements.doctorRooms.addEventListener("click", (event) => {
            if (event.target.matches('[data-action="open-room"]')) {
                const roomId = Number(event.target.dataset.room);
                const room = state.doctorRooms.find((r) => r.id === roomId);
                if (room) openRoom(room);
            } else if (event.target.matches('[data-action="start-call"]')) {
                const roomId = Number(event.target.dataset.room);
                startCall(roomId);
            }
        });
        if (elements.openRoomChat) elements.openRoomChat.addEventListener("click", () => {
            const roomId = Number(elements.openRoomChat.dataset.room);
            const room = state.patientRooms.find((r) => r.id === roomId);
            if (room) openRoom(room);
        });
        if (elements.toggleGuard) elements.toggleGuard.addEventListener("click", () => {
            alert("Guard button clicked");
            toggleAvailability("is_on_guard");
        });
        if (elements.toggleAppointments) elements.toggleAppointments.addEventListener("click", () => toggleAvailability("is_accepting"));
        if (elements.refreshDoctorRooms) elements.refreshDoctorRooms.addEventListener("click", () => {
            loadDoctorRooms();
            buildThreadList();
        });
        if (elements.refreshPatientRooms) elements.refreshPatientRooms.addEventListener("click", () => {
            loadPatientRooms();
            buildThreadList();
        });
        if (elements.threadList) elements.threadList.addEventListener("click", handleThreadClick);
        if (elements.chatForm) elements.chatForm.addEventListener("submit", sendChatMessage);
        if (elements.guardiaChatForm) elements.guardiaChatForm.addEventListener("submit", sendChatMessage);
        if (elements.closeChat) elements.closeChat.addEventListener("click", resetSelection);
        if (elements.exitGuardia) elements.exitGuardia.addEventListener("click", () => {
            if (elements.guardiaView) elements.guardiaView.setAttribute("hidden", "true");
        });
    } catch (e) {
        console.warn("Error in initEventListeners part 4:", e);
    }
    try {
        if (elements.personaButtons) elements.personaButtons.forEach((btn) => {
            btn.addEventListener("click", () => {
                if (state.user?.role !== "doctor") return;
                const view = btn.dataset.mode === "doctor" ? "doctor-view" : "patient-view";
                showDashboardView(view);
                if (elements.personaButtons) elements.personaButtons.forEach((other) => other.classList.toggle("active", other === btn));
            });
        });
        if (elements.emergencyButton) elements.emergencyButton.addEventListener("click", () => {
            if (elements.emergencyModal) elements.emergencyModal.removeAttribute("hidden");
            document.body.classList.add("modal-open");
        });
        if (elements.cancelEmergency) elements.cancelEmergency.addEventListener("click", () => {
            if (elements.emergencyModal) elements.emergencyModal.setAttribute("hidden", "true");
            document.body.classList.remove("modal-open");
        });
        if (elements.callEmergency) elements.callEmergency.addEventListener("click", () => {
            alert("Prototipo: marcariamos al servicio de emergencias.");
            if (elements.emergencyModal) elements.emergencyModal.setAttribute("hidden", "true");
            document.body.classList.remove("modal-open");
        });
        if (elements.profileForm) elements.profileForm.addEventListener("submit", saveProfile);
        if (elements.rejectCall) elements.rejectCall.addEventListener("click", () => respondCall(false));
        if (elements.acceptCall) elements.acceptCall.addEventListener("click", () => respondCall(true));
        window.addEventListener("resize", () => {
            if (window.innerWidth >= 1080) {
                document.body.classList.remove("menu-open");
            }
        });
    } catch (e) {
        console.warn("Error in initEventListeners part 5:", e);
    }
}

function handleSearch(event) {
    event.preventDefault();
    const name = document.getElementById("search-name").value.trim().toLowerCase();
    const guard = document.getElementById("search-guard").value;
    const accepting = document.getElementById("search-accepting").value;
    const filtered = state.doctors.filter((doctor) => {
        const matchName = !name || doctor.name.toLowerCase().includes(name);
        const matchGuard = guard === "any" || String(doctor.is_on_guard) === guard;
        const matchAccepting = accepting === "any" || String(doctor.is_accepting) === accepting;
        return matchName && matchGuard && matchAccepting;
    });
    renderDoctorList(filtered);
}

async function attemptAutoLogin() {
    if (!state.token) {
        showScreen(screens.login);
        return;
    }

    // Verify token is still valid by making a test request
    try {
        state.user = await apiFetch("/users/me");
        await onAuthReady();
    } catch (error) {
        console.warn("Auto login failed:", error.message);
        // Clear token only on auto-login failure
        setToken(null);
        showScreen(screens.login);
    }
}

// Delay init to ensure DOM is ready
setTimeout(initEventListeners, 100);
attemptAutoLogin();

async function startCall(roomId) {
    alert("Iniciando llamada para sala " + roomId);
    try {
        const room = await apiFetch(`/waiting-room/${roomId}/start-call`, { method: "PUT" });
        alert("Llamada iniciada, abriendo Jitsi");
        await loadDoctorRooms();
        // Open Jitsi for doctor
        openJitsiCall(roomId);
    } catch (error) {
        alert("Error iniciando llamada: " + error.message);
    }
}

function openJitsiCall(roomId) {
    const roomName = `medicapp-room-${roomId}`;
    const domain = 'meet.jit.si';
    const options = {
        roomName: roomName,
        width: '100%',
        height: '100%',
        parentNode: document.querySelector('#jitsi-container'),
        userInfo: {
            displayName: state.user.name,
        },
    };
    const api = new JitsiMeetExternalAPI(domain, options);
    elements.videoModal.removeAttribute("hidden");
    document.body.classList.add("modal-open");
    // Close button
    elements.closeVideo.onclick = () => {
        api.dispose();
        elements.videoModal.setAttribute("hidden", "true");
        document.body.classList.remove("modal-open");
    };
}

// New function to show call invite
function showCallInvite(roomId) {
    state.invitedRoomId = roomId;
    elements.callInviteModal.removeAttribute("hidden");
    document.body.classList.add("modal-open");
}

// Accept call button handler
document.getElementById("accept-call").onclick = async function() {
    const roomId = Number(document.getElementById("invite-room-id").textContent.split(": ")[1]);
    if (!roomId) return;
    try {
        // Join the room
        openRoom(state.patientRooms.find(r => r.id === roomId));
        // Start the call
        await startCall(roomId);
        // Close the invite modal
        document.getElementById("call-invite-modal").setAttribute("hidden", "true");
        document.body.classList.remove("modal-open");
    } catch (error) {
        alert("Error al aceptar la llamada: " + error.message);
    }
};

// Reject call button handler
document.getElementById("reject-call").onclick = function() {
    const inviteModal = document.getElementById("call-invite-modal");
    inviteModal.setAttribute("hidden", "true");
    document.body.classList.remove("modal-open");
};

function sendMiaMessage() {
    const message = elements.miaChatInput.value.trim();
    if (!message) return;
    addMiaMessage(message, true);
    elements.miaChatInput.value = "";
    // Simulate bot response
    setTimeout(() => {
        addMiaMessage("Gracias por tu mensaje. Estoy aquí para ayudarte. ¿Hay algo más en lo que pueda asistirte?", false);
    }, 1000);
}

function addMiaMessage(text, isUser) {
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${isUser ? "user-message" : "bot-message"}`;
    messageDiv.innerHTML = `
        <div class="message-avatar">${isUser ? "👤" : "🤖"}</div>
        <div class="message-content">
            <p>${text}</p>
        </div>
    `;
    elements.miaChatMessages.appendChild(messageDiv);
    elements.miaChatMessages.scrollTop = elements.miaChatMessages.scrollHeight;
}

async function loadDoctorsOnDuty() {
    try {
        const doctors = await apiFetch("/doctors");
        elements.doctorsOnDuty.innerHTML = "";
        doctors.forEach(doctor => {
            if (doctor.is_on_guard) {
                const doctorCard = document.createElement("div");
                doctorCard.className = "doctor-card";
                doctorCard.innerHTML = `
                    <div class="doctor-info">
                        <h4>${doctor.name}</h4>
                        <p>${doctor.specialty || "Médico General"} ${doctor.experience_years ? `(${doctor.experience_years} años exp.)` : ''}</p>
                    </div>
                    <div class="doctor-actions">
                        <button class="ghost-button ghost-sm" data-action="view-profile" data-doctor-id="${doctor.id}">Ver Perfil</button>
                        <button class="primary-button ghost-sm" data-action="join-waiting-room" data-doctor-id="${doctor.id}">Sala de Espera</button>
                    </div>
                `;
                elements.doctorsOnDuty.appendChild(doctorCard);
            }
        });
        if (doctors.filter(d => d.is_on_guard).length === 0) {
            elements.doctorsOnDuty.innerHTML = "<p>No hay médicos de guardia disponibles en este momento.</p>";
        }
    } catch (error) {
        console.error("Error loading doctors:", error);
        elements.doctorsOnDuty.innerHTML = "<p>Error al cargar médicos.</p>";
    }
}

async function viewDoctorProfile(doctorId) {
    try {
        const doctor = await apiFetch(`/doctors/${doctorId}`);
        const ratings = await apiFetch(`/doctors/${doctorId}/ratings`);
        const avgRating = ratings.length > 0 ? (ratings.reduce((sum, r) => sum + r.rating, 0) / ratings.length).toFixed(1) : 'Sin calificaciones';
        const stars = '⭐'.repeat(Math.round(avgRating)) || 'Sin calificaciones';
        let profileText = `Perfil de ${doctor.name}\nEspecialidad: ${doctor.specialty || 'No especificada'}\nExperiencia: ${doctor.experience_years || 'No especificada'} años\nCalificación promedio: ${avgRating} ${stars}\n\nComentarios:\n`;
        ratings.forEach(r => {
            profileText += `⭐${r.rating}: ${r.comment || 'Sin comentario'}\n`;
        });
        alert(profileText);
    } catch (error) {
        alert("Error al cargar perfil del médico: " + error.message);
    }
}

async function joinWaitingRoom(doctorId) {
    try {
        const response = await apiFetch("/waiting-rooms", {
            method: "POST",
            body: JSON.stringify({ doctor_id: doctorId })
        });
        state.currentRoom = response;
        showWaitingApprovalView();
    } catch (error) {
        alert("Error al unirse a la sala de espera: " + error.message);
    }
}

function showWaitingApprovalView() {
    // Hide current view and show waiting approval
    elements.guardiaContent.innerHTML = `
        <div class="waiting-approval">
            <h2>Esperando Aprobación</h2>
            <p>El médico está revisando tu solicitud. Por favor espera...</p>
            <div class="loading-spinner"></div>
        </div>
    `;
    // Start polling for approval
    pollForApproval();
}

async function pollForApproval() {
    const pollInterval = setInterval(async () => {
        try {
            const room = await apiFetch(`/waiting-rooms/${state.currentRoom.id}`);
            if (room.status === "approved") {
                clearInterval(pollInterval);
                showWaitingRoomView(room);
            } else if (room.status === "rejected") {
                clearInterval(pollInterval);
                alert("Tu solicitud fue rechazada por el médico.");
                showDashboardView("patient-view");
            }
        } catch (error) {
            console.error("Error polling for approval:", error);
        }
    }, 2000); // Poll every 2 seconds
}

function showWaitingRoomView(room) {
    elements.guardiaContent.innerHTML = `
        <div class="waiting-room-status">
            <h2>Sala de Espera</h2>
            <p>Estás en la sala de espera del Dr. ${room.doctor_name}</p>
            <p>Personas delante tuyo: <span class="queue-position">${room.queue_position || 0}</span></p>
            <p>El médico te llamará pronto.</p>
        </div>
    `;
    // Start polling for call
    pollForCall(room.id);
}

async function pollForCall(roomId) {
    const pollInterval = setInterval(async () => {
        try {
            const room = await apiFetch(`/waiting-rooms/${roomId}`);
            if (room.call_status === "calling") {
                clearInterval(pollInterval);
                // Simulate call acceptance
                if (confirm("El médico te está llamando. ¿Aceptar la llamada?")) {
                    startVideoCall(room.doctor_id);
                } else {
                    // Reject call
                    showRatingView(room.doctor_id);
                }
            }
        } catch (error) {
            console.error("Error polling for call:", error);
        }
    }, 2000);
}

function startVideoCall(doctorId) {
    // Integrate with existing video call logic
    openJitsiCall(doctorId);
    // After call ends, show rating
    // For now, simulate after 10 seconds
    setTimeout(() => {
        showRatingView(doctorId);
    }, 10000);
}

function showRatingView(doctorId) {
    elements.guardiaContent.innerHTML = `
        <div class="rating-view">
            <h2>Calificar Atención</h2>
            <p>¿Cómo calificarías la atención del médico?</p>
            <div class="stars">
                <span class="star" data-rating="1">⭐</span>
                <span class="star" data-rating="2">⭐</span>
                <span class="star" data-rating="3">⭐</span>
                <span class="star" data-rating="4">⭐</span>
                <span class="star" data-rating="5">⭐</span>
            </div>
            <textarea id="rating-comment" placeholder="Comentario opcional..."></textarea>
            <button id="submit-rating" class="primary-button">Enviar Calificación</button>
        </div>
    `;
    // Add event listeners for stars
    document.querySelectorAll('.star').forEach(star => {
        star.addEventListener('click', (e) => {
            const rating = e.target.dataset.rating;
            document.querySelectorAll('.star').forEach(s => s.classList.remove('selected'));
            for (let i = 0; i < rating; i++) {
                document.querySelectorAll('.star')[i].classList.add('selected');
            }
        });
    });
    document.getElementById('submit-rating').addEventListener('click', () => {
        const rating = document.querySelectorAll('.star.selected').length;
        const comment = document.getElementById('rating-comment').value;
        submitRating(doctorId, rating, comment);
    });
}

async function submitRating(doctorId, rating, comment) {
    try {
        await apiFetch('/ratings', {
            method: 'POST',
            body: JSON.stringify({ doctor_id: doctorId, rating, comment })
        });
        alert('¡Gracias por tu calificación!');
        showDashboardView('patient-view');
    } catch (error) {
        alert('Error al enviar calificación: ' + error.message);
    }
}

async function respondCall(accept) {
    alert(accept ? "Aceptando llamada" : "Rechazando llamada");
    try {
        const room = await apiFetch(`/waiting-room/${state.invitedRoomId}/respond-call?accept=${accept}`, { method: "PUT" });
        elements.callInviteModal.setAttribute("hidden", "true");
        document.body.classList.remove("modal-open");
        if (accept) {
            alert("Abriendo Jitsi para paciente");
            openJitsiCall(state.invitedRoomId);
        }
        await loadPatientRooms();
    } catch (error) {
        alert("Error respondiendo llamada: " + error.message);
    }
}

