document.addEventListener('DOMContentLoaded', function () {
    console.log('[JS] DOMContentLoaded');
    const socket = io(window.location.origin); // Свързва се към същия хост и порт

    // --- Глобални променливи за фронтенда ---
    let currentTranslations = {}; // Ще държи преводите за ТЕКУЩИЯ език
    let currentLang = document.documentElement.lang || 'bg'; // Вземаме от HTML или 'bg'
    let supportedLanguages = {}; // Ще се попълни от сървъра

    // --- DOM елементи ---
    const operatorLoginOverlay = document.getElementById('operator-login-overlay');
    const operatorIdDisplay = document.getElementById('operator-id-display');
    const operatorNameDisplay = document.getElementById('operator-name');
    const travelLotIdDisplay = document.getElementById('travel-lot-id-display');
    const productNumberDisplay = document.getElementById('product-number');
    const productDescriptionDisplay = document.getElementById('product-description');
    const orderNumberDisplay = document.getElementById('order-number');
    const productionQuantityDisplay = document.getElementById('production-quantity');
    const logPanel = document.getElementById('log-panel');
    const langSelect = document.getElementById('language-select');
    const overallStatusIndicator = document.getElementById('overall-status-indicator');
    const overallStatusText = document.getElementById('overall-status-text');

    // --- Основни Функции ---
    function updateDateTime() {
        const now = new Date();
        const options = { year: 'numeric', month: 'long', day: 'numeric' };
        const timeOptions = { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false };
        let locale = 'en-US';
        if (currentLang === 'bg') locale = 'bg-BG';
        else if (currentLang === 'sr') locale = 'sr-RS';
        const dateString = now.toLocaleDateString(locale, options);
        const timeString = now.toLocaleTimeString(locale, timeOptions);
        const dateTimeEl = document.getElementById('current-datetime');
        if (dateTimeEl) {
            dateTimeEl.textContent = `${dateString} ${timeString}`;
        }
    }

    function getTranslation(key) {
        if (!currentTranslations || Object.keys(currentTranslations).length === 0) {
            // console.warn(`[JS getTranslation] No translations loaded for currentLang '${currentLang}'. Key: ${key}`);
            return key; // Връщаме ключа, ако няма заредени преводи
        }
        const keys = key.split('.');
        let result = currentTranslations;
        for (const k of keys) {
            if (result && typeof result === 'object' && k in result) {
                result = result[k];
            } else {
                // console.warn(`[JS getTranslation] Key '${key}' (part '${k}') not found.`);
                return key; // Връщаме оригиналния ключ, ако част от него липсва
            }
        }
        return result !== undefined ? result : key;
    }

    function applyTranslations() {
        console.log(`[JS applyTranslations] Applying translations for lang: ${currentLang}`);
        if (!currentTranslations || Object.keys(currentTranslations).length === 0) {
            console.warn(`[JS applyTranslations] No translations available for ${currentLang}. Requesting from server.`);
            socket.emit('request_initial_data', { lang: currentLang }); // Поискай преводите отново
            return;
        }

        document.documentElement.lang = currentLang;
        if (langSelect) langSelect.value = currentLang;
        document.title = getTranslation('appTitle');

        document.querySelectorAll('[data-translate-key]').forEach(element => {
            const key = element.getAttribute('data-translate-key');
            if (!key) return;

            const translation = getTranslation(key);
            // console.log(`[JS translateElement] Key: '${key}', Translation: '${translation}'`);

            if (element.hasAttribute('data-translate-placeholder')) {
                element.placeholder = translation;
            } else {
                // Опростена логика: опитва се да намери първия текстов възел или директно задава textContent
                let firstTextNode = Array.from(element.childNodes).find(node => node.nodeType === Node.TEXT_NODE && node.textContent.trim().length > 0);
                if (firstTextNode && (!element.children.length || !Array.from(element.children).some(child => child.hasAttribute('data-translate-key')))) {
                    // Ако има текстов възел и няма преводими деца, или елементът е прост
                     let suffix = "";
                     if (element.querySelector('span[id$="-text"]')) { // Ако има вътрешен span за статус
                         if (firstTextNode.textContent.includes(': ')) {
                             suffix = ": ";
                         } else if (firstTextNode.textContent.includes(' ')) {
                             suffix = " ";
                         }
                     }
                    firstTextNode.textContent = translation + suffix;
                } else {
                    // За елементи, които са основно контейнери за други преводими елементи, не правим нищо
                    // или ако елементът е предназначен да показва само превода
                    if (element.children.length === 0 || ['H1', 'H2', 'H3', 'H4', 'BUTTON', 'LABEL', 'P', 'OPTION'].includes(element.tagName)) {
                         element.textContent = translation;
                    }
                }
            }
        });
        updateDateTime();
    }

    function changeLanguage(newLang) {
        if (supportedLanguages && supportedLanguages[newLang] && newLang !== currentLang) {
            console.log(`[JS changeLanguage] User selected: ${newLang}. Current: ${currentLang}. Emitting 'language_changed'.`);
            localStorage.setItem('preferredLanguage', newLang);
            currentLang = newLang; // Оптимистично обновяване
            // Сървърът ще изпрати 'initial_data' с новите преводи,
            // което ще задейства translatePage() от 'initial_data' хендлъра.
            socket.emit('language_changed', { lang: newLang });
        }
    }

    function updateElementText(element, textKey, defaultText = '--', removeTranslateKey = true) {
        if (element) {
            if (textKey) {
                element.textContent = getTranslation(textKey);
                element.setAttribute('data-translate-key', textKey);
            } else {
                element.textContent = defaultText;
                if (removeTranslateKey) {
                    element.removeAttribute('data-translate-key');
                }
            }
        }
    }

    function updateOperatorSection(operatorData) {
        if (operatorData && operatorData.name) {
            if(operatorIdDisplay) operatorIdDisplay.textContent = operatorData.id;
            if(operatorNameDisplay) {
                operatorNameDisplay.textContent = operatorData.name;
                operatorNameDisplay.removeAttribute('data-translate-key');
            }
        } else {
            if(operatorIdDisplay) operatorIdDisplay.textContent = '--';
            if(operatorNameDisplay) {
                operatorNameDisplay.textContent = getTranslation('operatorSection.nameDefault');
                operatorNameDisplay.setAttribute('data-translate-key', 'operatorSection.nameDefault');
            }
        }
    }

    function updateTravelLotSection(travelLotData) {
        if (travelLotData) {
            if(travelLotIdDisplay) travelLotIdDisplay.textContent = travelLotData.id || '--';
            if(productNumberDisplay) productNumberDisplay.textContent = travelLotData.productNumber || '--';
            if(productDescriptionDisplay) productDescriptionDisplay.textContent = travelLotData.description || '--';
            if(orderNumberDisplay) orderNumberDisplay.textContent = travelLotData.orderNumber || '--';
            if(productionQuantityDisplay) productionQuantityDisplay.textContent = travelLotData.quantity || '--';
        } else {
            if(travelLotIdDisplay) travelLotIdDisplay.textContent = '--';
            if(productNumberDisplay) productNumberDisplay.textContent = '--';
            if(productDescriptionDisplay) productDescriptionDisplay.textContent = '--';
            if(orderNumberDisplay) orderNumberDisplay.textContent = '--';
            if(productionQuantityDisplay) productionQuantityDisplay.textContent = '--';
        }
    }

    function updateOverallStatus(statusKey) {
        if (!overallStatusIndicator || !overallStatusText) return;
        const statusClass = statusKey ? statusKey.split('.')[1] || 'idle' : 'idle';
        overallStatusIndicator.className = 'status-indicator status-' + statusClass;
        overallStatusText.textContent = getTranslation(statusKey); // Превеждаме тук
        overallStatusText.setAttribute('data-translate-key', statusKey);
    }

    function updateStatusIndicator(elementId, statusKey) {
        const indicator = document.getElementById(elementId + "-indicator");
        const textElement = document.getElementById(elementId + "-text");
        if (!indicator || !textElement) return;
        const statusClass = statusKey ? statusKey.split('.')[1] || 'idle' : 'idle';
        indicator.className = 'status-indicator status-' + statusClass;
        textElement.textContent = getTranslation(statusKey); // Превеждаме тук
        textElement.setAttribute('data-translate-key', statusKey);
    }

    function updateTurntablePosition(turntable, position, data) {
        const baseId = `v${turntable}p${position}`;
        const statusIndicator = document.getElementById(`${baseId}-status-indicator`);
        const statusTextEl = document.getElementById(`${baseId}-status`);
        const moduleIdEl = document.getElementById(`${baseId}-module-id`);
        const moduleIdsEl = document.getElementById(`${baseId}-module-ids`);
        const timeEl = document.getElementById(`${baseId}-time`);
        const progressEl = document.getElementById(`${baseId}-progress`);

        if (statusIndicator && statusTextEl && data && data.status) {
            const statusKey = data.status;
            const statusClass = statusKey.split('.')[1] || 'idle';
            statusIndicator.className = 'status-indicator status-' + statusClass;
            statusTextEl.textContent = getTranslation(statusKey);
            statusTextEl.setAttribute('data-translate-key', statusKey);
        }
        if (moduleIdEl && data) moduleIdEl.textContent = data.moduleId || '--';
        if (moduleIdsEl && data) moduleIdsEl.textContent = Array.isArray(data.moduleIds) ? data.moduleIds.join(', ') : (data.moduleIds || '--');
        if (timeEl && data && data.time !== undefined) timeEl.textContent = data.time;
        if (progressEl && data) progressEl.style.width = `${data.progress || 0}%`;
    }

    function addLogEntry(message, level = 'info', isRawMessage = false) {
        if (!logPanel) return;
        const entryDiv = document.createElement('div');
        entryDiv.classList.add('log-entry', `log-${level}`);
        const timestamp = new Date().toLocaleTimeString(currentLang === 'bg' ? 'bg-BG' : (currentLang === 'sr' ? 'sr-RS' : 'en-US'), { hour12: false });
        let displayMessage = message;
        if (!isRawMessage && jsTranslations[currentLang] && Object.keys(jsTranslations[currentLang]).length > 0) {
            displayMessage = getTranslation(message);
        } else if (!isRawMessage) {
            displayMessage = message;
        }
        entryDiv.textContent = `[${timestamp}] ${displayMessage}`;
        logPanel.insertBefore(entryDiv, logPanel.firstChild);
        while (logPanel.childNodes.length > 100) {
            logPanel.removeChild(logPanel.lastChild);
        }
    }

    function setLoginOverlayState(show, operatorData = null) {
        if (!operatorLoginOverlay) return;

        if (show) {
            operatorLoginOverlay.style.display = 'flex';
            console.log('[JS setLoginOverlayState] Showing login overlay.');
            // Превеждаме текстовете на овърлея ВЕДНАГА
            const promptEl = operatorLoginOverlay.querySelector('[data-translate-key="login.prompt"]');
            if (promptEl) promptEl.textContent = getTranslation("login.prompt");
            const waitingEl = operatorLoginOverlay.querySelector('[data-translate-key="login.waiting"]');
            if (waitingEl) waitingEl.textContent = getTranslation("login.waiting");
        } else {
            operatorLoginOverlay.style.display = 'none';
            console.log('[JS setLoginOverlayState] Hiding login overlay.');
        }
        updateOperatorSection(operatorData);
        updateButtonStates(!!(operatorData && operatorData.name));
    }

    // SocketIO Event Handlers
    socket.on('connect', () => {
        console.log('[JS] Connected to server via Socket.IO');
        const savedLang = localStorage.getItem('preferredLanguage') || document.documentElement.lang || 'bg';
        currentLang = savedLang; // Задаваме currentLang тук за addLogEntry
        if (langSelect) langSelect.value = currentLang;
        socket.emit('request_initial_data', { lang: currentLang });
        // addLogEntry ще се извика от 'initial_data'
    });

    socket.on('disconnect', (reason) => {
        console.error('[JS] Disconnected from server:', reason);
        addLogEntry(getTranslation('socket.disconnected') + `: ${reason}`, 'error', true);
        updateOverallStatus('status.disconnected');
    });

    socket.on('connect_error', (error) => {
        console.error('[JS] Connection error with server:', error);
        addLogEntry(getTranslation('socket.connectError') + `: ${error.message}`, 'error', true);
        updateOverallStatus('status.disconnected');
        setLoginOverlayState(true); // Показваме овърлея при грешка с връзката
    });

    socket.on('initial_data', (data) => {
        console.log('[JS] INITIAL_DATA received:', data); // Не го прави JSON.stringify за по-лесен преглед в конзолата

        currentLang = data.current_lang || 'en';
        supportedLanguages = data.supported_languages || {};

        if (data.translations && typeof data.translations === 'object') {
            jsTranslations[currentLang] = data.translations;
            console.log(`[JS initial_data] Stored translations for ${currentLang}:`, jsTranslations[currentLang]);
        } else {
            console.error("[JS initial_data] Translations not received or in unexpected format:", data.translations);
            jsTranslations[currentLang] = {}; // Инициализираме като празен обект
        }

        if (langSelect) {
            langSelect.innerHTML = '';
            Object.keys(supportedLanguages).forEach(code => {
                const option = document.createElement('option');
                option.value = code;
                option.textContent = supportedLanguages[code];
                langSelect.appendChild(option);
            });
            langSelect.value = currentLang;
        }

        translatePage(currentLang); // Превеждаме цялата страница с новите/първоначалните преводи

        if (socket.connected) {
             addLogEntry('socket.connected', 'success'); // Сега вече имаме преводи
        }

        let operatorIsLoggedIn = false;
        if (data.line_status) {
            const ls = data.line_status;
            updateOverallStatus(ls.overall_status);

            ['1', '2', '3'].forEach(robotNum => {
                if (ls.robots && ls.robots[robotNum]) updateStatusIndicator(`robot${robotNum}-status`, ls.robots[robotNum].status);
            });
            ['1', '2', '3', '4'].forEach(posNum => {
                if (ls.turntable1 && ls.turntable1[posNum]) updateTurntablePosition(1, posNum, ls.turntable1[posNum]);
                if (ls.turntable2 && ls.turntable2[posNum]) updateTurntablePosition(2, posNum, ls.turntable2[posNum]);
            });
            if (ls.trays) {
                if (ls.trays.in) updateStatusIndicator('tray-in-status', ls.trays.in.status);
                if (ls.trays.out) updateStatusIndicator('tray-out-status', ls.trays.out.status);
            }
            updateTravelLotSection(ls.current_travel_lot);

            if (ls.current_operator && ls.current_operator.name) {
                operatorIsLoggedIn = true;
            }
        } else {
             console.warn("[JS initial_data] 'line_status' is missing in data from server.");
        }
        // Управление на видимостта на овърлея и данните за оператор
        setLoginOverlayState(!operatorIsLoggedIn, data.line_status ? data.line_status.current_operator : null);
    });

    socket.on('require_operator_login', () => {
        console.log('[JS] require_operator_login received.');
        setLoginOverlayState(true); // Показва овърлея и превежда текстовете му
        addLogEntry('log.operatorLoginRequired', 'warning');
    });

    socket.on('operator_status_update', (data) => {
        console.log('[JS] OPERATOR_STATUS_UPDATE received:', data);
        const isLoggedIn = !!(data.operator && data.operator.name);
        console.log('[JS operator_status_update] isLoggedIn based on event data:', isLoggedIn);

        setLoginOverlayState(!isLoggedIn, data.operator); // Показва/скрива овърлея и обновява данните за оператора
    });

    socket.on('travel_lot_update', (data) => {
        console.log('[JS] Travel lot update:', data);
        updateTravelLotSection(data.travel_lot);
    });

    socket.on('update_status', (data) => {
        // console.log('[JS] Live status update received:', data);
        if (data.line_status) {
            const ls = data.line_status;
            if (ls.overall_status !== undefined) updateOverallStatus(ls.overall_status);
            if (ls.robots) {
                for (const robotNum in ls.robots) {
                    if (ls.robots[robotNum]) updateStatusIndicator(`robot${robotNum}-status`, ls.robots[robotNum].status);
                }
            }
            if (ls.turntable1) {
                for (const posNum in ls.turntable1) {
                     if (ls.turntable1[posNum]) updateTurntablePosition(1, posNum, ls.turntable1[posNum]);
                }
            }
            if (ls.turntable2) {
                for (const posNum in ls.turntable2) {
                    if (ls.turntable2[posNum]) updateTurntablePosition(2, posNum, ls.turntable2[posNum]);
                }
            }
            if (ls.trays) {
                if (ls.trays.in) updateStatusIndicator('tray-in-status', ls.trays.in.status);
                if (ls.trays.out) updateStatusIndicator('tray-out-status', ls.trays.out.status);
            }
        }
    });

    socket.on('log_message', (log) => {
        addLogEntry(log.message, log.level, true);
    });

    updateDateTime();
    setInterval(updateDateTime, 1000);

    const startShiftBtn = document.getElementById('start-shift-btn');
    const endShiftBtn = document.getElementById('end-shift-btn');
    const loadTravelCardBtn = document.getElementById('load-travel-card-btn');
    const clearTravelCardBtn = document.getElementById('clear-travel-card-btn');

    function updateButtonStates(operatorLoggedIn) {
        if (startShiftBtn) startShiftBtn.disabled = operatorLoggedIn;
        if (endShiftBtn) endShiftBtn.disabled = !operatorLoggedIn;
        if (loadTravelCardBtn) loadTravelCardBtn.disabled = !operatorLoggedIn;
    }
    updateButtonStates(false); // Първоначална настройка

    if (startShiftBtn) {
        startShiftBtn.addEventListener('click', () => {
            const opName = operatorNameDisplay ? operatorNameDisplay.textContent : "";
            const opId = operatorIdDisplay ? operatorIdDisplay.textContent : "";
            if (!opId || opId === '--' || opName === getTranslation('operatorSection.nameDefault')) {
                addLogEntry("log.scanOperatorToStartShift", "warning");
            } else {
                addLogEntry(getTranslation("log.shiftAlreadyStarted") + `: ${opName}`, "info", true);
            }
        });
    }

    if (endShiftBtn) {
        endShiftBtn.addEventListener('click', () => {
            const opName = operatorNameDisplay ? operatorNameDisplay.textContent : "";
            const opId = operatorIdDisplay ? operatorIdDisplay.textContent : "";
            if (opId && opId !== '--' && opName !== getTranslation('operatorSection.nameDefault')) {
                socket.emit('operator_logout_request');
            } else {
                addLogEntry("log.noActiveShiftToEnd", "warning");
            }
        });
    }

    if (loadTravelCardBtn) {
        loadTravelCardBtn.addEventListener('click', () => {
            addLogEntry("log.scanTravelCardPrompt", "info");
        });
    }

    if (clearTravelCardBtn) {
        clearTravelCardBtn.addEventListener('click', () => {
            socket.emit('clear_travel_card_request');
        });
    }

    // Първоначално показване на овърлея - ще се управлява от initial_data
    // if (operatorLoginOverlay) {
    //     operatorLoginOverlay.style.display = 'flex';
    //     console.log('[JS DOMContentLoaded] Initially showing login overlay. Translation will occur upon receiving initial_data.');
    // }
});