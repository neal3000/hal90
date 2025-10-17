// Global state
let appState = {};

// Initialize app
async function initApp() {
    try {
        appState = await eel.get_app_state()();
        updateInterface();
        setupScreensaver();
    } catch (error) {
        console.error('Failed to initialize app:', error);
    }
}

// Handle screen clicks
async function handleClick() {
    await eel.handle_click()();
}

// Reset screensaver timeout
function resetScreensaverTimeout() {
    // TODO: Implement screensaver logic
}

// Update interface based on state
function updateInterface() {
    const appElement = document.getElementById('app');
    const contentElement = document.getElementById('content');
    
    // Update ribbon class
    appElement.className = `action-ribbon ${getRibbonClass(appState.status)}`;
    
    // Update content
    contentElement.innerHTML = renderContent();
}

function getRibbonClass(status) {
    const classMap = {
        'RECORDING': 'record',
        'IDLE': 'idle',
        'THINKING': 'rainbow',
        'BOOT': 'idle',
        'PROCESSING_RECORDING': 'rainbow',
        'SPEAKING': '',
        'SCREENSAVER': ''
    };
    return classMap[status] || '';
}

function renderContent() {
    if (appState.show_face) {
        return renderFace(appState.face);
    }
    
    if (appState.status_message) {
        return renderStatusMessage(appState.internal_message);
    }
    
    return renderWords(
        appState.backend_response,
        appState.recorded_message,
        appState.reaction,
        appState.finished_streaming
    );
}

function renderFace(face) {
    // TODO: Implement face animation system
    // This would need to recreate your Faces.jsx logic
    return `
        <div class="faces-container">
            <span class="face-float-animation">
                <img class="face-filter-hue" src="assets/faces/smile_eyes_opened.png" alt="${face}" />
            </span>
        </div>
    `;
}

function renderStatusMessage(message) {
    return `
        <div class="status-message-container">
            <span class="status-message-text">${message}</span>
        </div>
    `;
}

function renderWords(backendResponse, recordedMessage, reaction, finished) {
    const hasResponse = backendResponse && backendResponse.length > 0;
    const textContent = hasResponse ? backendResponse.join('') : recordedMessage;
    const textClass = hasResponse ? 'llm-output-text' : 'llm-output-recorded';
    
    return `
        <div>
            <div class="llm-output-container">
                <span class="${textClass}">${textContent}</span>
            </div>
            ${renderReaction(reaction, finished)}
        </div>
    `;
}

function renderReaction(reaction, finished) {
    if (!finished) {
        return renderSpeaking();
    }
    
    const imageName = reaction || 'neutral';
    return `
        <div class="reaction-image-container face-float-animation">
            <img class="reaction-image face-filter-hue" src="assets/reactions/${imageName}.png" alt="${imageName}" />
        </div>
    `;
}

function renderSpeaking() {
    // TODO: Implement mouth animation
    return `
        <div class="reaction-image-container">
            <div class="face-stack">
                <img class="face-base face-filter-hue" src="assets/speaking/still.png" alt="face" />
                <img class="mouth-overlay face-filter-hue" src="assets/speaking/open1.png" alt="mouth" />
            </div>
        </div>
    `;
}

function setupScreensaver() {
    // TODO: Implement screensaver timeout logic
}

// Listen for state updates from Python
eel.expose(updateState);
function updateState(newState) {
    appState = { ...appState, ...newState };
    updateInterface();
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', initApp);