document.addEventListener('DOMContentLoaded', function () {
    console.log('[JS] DOMContentLoaded - Финална версия заредена.');

    const socket = io(window.location.origin);
    const langSelect = document.getElementById('language-select');
    const taskTitle = document.getElementById('task-title');
    const taskInstruction = document.getElementById('task-instruction');
    const operatorIdDisplay = document.getElementById('operator-id-display');
    const operatorNameDisplay = document.getElementById('operator-name-display');
    const logoutBtn = document.getElementById('logout-btn');
    const travelLotIdDisplay = document.getElementById('travel-lot-id-display');
    const productNumberDisplay = document.getElementById('product-number-display');
    const logPanel = document.getElementById('log-panel');
    const overallStatusIndicator = document.getElementById('overall-status-indicator');
    const overallStatusText = document.getElementById('overall-status-text');

    // При другите декларации на елементи
    const moduleActionsPanel = document.getElementById('module-actions-panel');
    const actionModuleIdSpan = document.getElementById('action-module-id');
    const btnStartTestTester1 = document.getElementById('btn-start-test-tester1');

    let state = {
        currentStep: 'awaiting_operator',
        operator: null,
        travelLot: null,
        translations: {}
    };

    function getTranslation(key) {
        if (!key || typeof key !== 'string') return '';
        const keys = key.split('.');
        let result = state.translations;
        for (const k of keys) {
            if (result && typeof result === 'object' && k in result) {
                result = result[k];
            } else {
                return key;
            }
        }
        return result;
    }

    function updateUI() {
        console.log(`[UI] Обновяване на UI. Текуща стъпка: ${state.currentStep}`);
        if (taskTitle && taskInstruction) {
            switch (state.currentStep) {
                case 'awaiting_operator':
                    taskTitle.textContent = getTranslation('task.scanOperator');
                    taskInstruction.textContent = getTranslation('task.waitingForScan');
                    break;
                case 'awaiting_travel_lot':
                    taskTitle.textContent = getTranslation('task.scanTravelLot');
                    taskInstruction.innerHTML = `${getTranslation('task.operatorIdentified')}: <strong>${state.operator.name}</strong>. ${getTranslation('task.scanTravelLotPrompt')}`;
                    break;
                case 'ready':
                    taskTitle.textContent = getTranslation('task.ready');
                    taskInstruction.textContent = getTranslation('task.systemReadyPrompt');
                    break;
            }
        }
        if(operatorIdDisplay && operatorNameDisplay) {
            operatorIdDisplay.textContent = state.operator ? state.operator.id : '--';
            operatorNameDisplay.textContent = state.operator ? state.operator.name : getTranslation('operatorSection.nameDefault');
        }
        if(travelLotIdDisplay && productNumberDisplay) {
            travelLotIdDisplay.textContent = state.travelLot ? state.travelLot.id : '--';
            productNumberDisplay.textContent = state.travelLot ? state.travelLot.productNumber : '--';
        }
        if(logoutBtn) {
            logoutBtn.style.display = state.operator ? 'block' : 'none';
        }
    }

    function addLogEntry(message, level = 'info') {
        if (!logPanel) return;
        const translatedMessage = getTranslation(message);
        const entryDiv = document.createElement('div');
        entryDiv.classList.add('log-entry', `log-${level}`);
        const timestamp = new Date().toLocaleTimeString('bg-BG');
        entryDiv.innerHTML = `<span class="text-gray-500 mr-2">${timestamp}</span> &raquo; <span class="ml-1">${translatedMessage}</span>`;
        logPanel.insertBefore(entryDiv, logPanel.firstChild);
    }

    function handleStatusUpdate(data) {
        if (!data) return;
        if (overallStatusIndicator && overallStatusText && data.overall_status) {
            const statusKey = data.overall_status.split('.')[1] || 'idle';
            overallStatusIndicator.className = 'status-indicator ' + statusKey;
            overallStatusText.textContent = getTranslation(data.overall_status);
        }
        if (data.robots) {
            for (let i = 1; i <= 3; i++) {
                const robotStatusText = document.getElementById(`robot${i}-status-text`);
                const robotStatusIndicator = document.getElementById(`robot${i}-status-indicator`);
                if (robotStatusText && robotStatusIndicator && data.robots[i] && data.robots[i].status) {
                    const robotStatusKey = data.robots[i].status.split('.')[1] || 'idle';
                    robotStatusIndicator.className = 'status-indicator ' + robotStatusKey;
                    robotStatusText.textContent = getTranslation(data.robots[i].status);
                }
            }
        }
    }

    socket.on('connect', () => {
        console.log('Успешно свързан към сървъра.');
        socket.emit('request_initial_data');
    });

    socket.on('initial_data', (data) => {
        console.log('Получени начални данни.');
        if (data.translations) {
            state.translations = data.translations;
        }
        document.querySelectorAll('[data-translate-key]').forEach(element => {
            element.textContent = getTranslation(element.getAttribute('data-translate-key'));
        });
        if (data.line_status) {
            handleStatusUpdate(data.line_status);
        }
        updateUI();
    });

    socket.on('update_status', handleStatusUpdate);

    socket.on('barcode_scanned', (data) => {
        const barcode = data.barcode;
        addLogEntry(`Получен баркод: ${barcode}`);
        if (state.currentStep === 'awaiting_operator') {
            taskInstruction.textContent = `${getTranslation('log.validatingOperator').replace('{badge_id}', barcode)}...`;
            socket.emit('validate_operator', { 'barcode': barcode });
        } else if (state.currentStep === 'awaiting_travel_lot') {
            taskInstruction.textContent = `Проверка на маршрутна карта: ${barcode}...`;
            socket.emit('validate_travel_lot', { 'barcode': barcode });
        }
    });

    socket.on('operator_validation_result', (data) => {
        if (data.is_valid) {
            addLogEntry(getTranslation('log.operatorLoggedIn').replace('{operator_name}', data.operator_info.name), 'success');
            state.operator = data.operator_info;
            state.currentStep = 'awaiting_travel_lot';
        } else {
            addLogEntry('Сканираният бадж не е валиден!', 'error');
            state.operator = null;
            state.currentStep = 'awaiting_operator';
        }
        updateUI();
    });

    socket.on('travel_lot_validation_result', (data) => {
        if (data.is_valid) {
            let message = getTranslation('log.travelLotIdentified').replace('{lot_id}', data.travel_lot_info.id).replace('{item_number}', data.travel_lot_info.productNumber);
            addLogEntry(message, 'success');
            state.travelLot = data.travel_lot_info;
            state.currentStep = 'ready';
        } else {
            addLogEntry('Сканираната маршрутна карта не е валидна!', 'error');
        }
        updateUI();
    });


    // Функция, която да показва панела с действия за даден модул
    function showModuleActions(moduleId) {
        if (moduleActionsPanel && actionModuleIdSpan) {
            actionModuleIdSpan.textContent = moduleId;
            moduleActionsPanel.style.display = 'block';
            // Тук може да зададете и IP адреса на тестера, ако е динамичен
            // localStorage.setItem('currentModuleForAction', moduleId);
        }
    }

    if (btnStartTestTester1) {
        btnStartTestTester1.addEventListener('click', () => {
            const moduleId = actionModuleIdSpan.textContent; // Вземаме ID-то на модула
            if (!moduleId || moduleId === '--') {
                addLogEntry('Моля, първо изберете/сканирайте модул.', 'warning');
                return;
            }

            // Примерни данни - IP адресът и портът на Тестер 1 трябва да са конфигурируеми
            // Може да ги вземете от Config файла чрез initial_data, или да ги имате в JS
            const tester1_ip = "192.168.1.101"; // ЗАМЕНЕТЕ С РЕАЛНИЯ IP
            const tester1_port = 8000;          // ЗАМЕНЕТЕ С РЕАЛНИЯ ПОРТ
            const test_name = "full_functional_test"; // Примерно име на тест

            console.log(`[JS] Изпращане на команда за старт на тест към Тестер 1 за модул: ${moduleId}`);
            socket.emit('trigger_start_test_on_device', {
                module_id: moduleId,
                device_ip: tester1_ip,
                device_port: tester1_port,
                test_name: test_name
            });
        });
    }

    // Трябва да имате и хендлър за 'test_initiation_result' и 'ui_notification'
    socket.on('test_initiation_result', (data) => {
        if (data.success) {
            addLogEntry(data.message, 'success');
        } else {
            addLogEntry(data.message, 'error');
        }
    });

    socket.on('ui_notification', (data) => {
        addLogEntry(data.message, data.level);
    });

    socket.on('log_message', (log) => {
        addLogEntry(log.message, log.level);
    });

    socket.on('disconnect', () => {
        addLogEntry('Връзката със сървъра е прекъсната!', 'error');
    });

    if (langSelect) {
        langSelect.addEventListener('change', function() {
            window.location.href = `/set_language/${this.value}`;
        });
    }

    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            addLogEntry(getTranslation('log.operatorLoggedOut'), 'info');
            socket.emit('logout_request');
        });
    }
});