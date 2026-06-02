/* ==========================================================================
   GRAVITY FLIP POKER - ELITE INTERACTIVE WEB APP SCRIPT
   Web Audio API Synthesis, Canvas Confetti Particles, 3D Deal Actions, REST APIs
   ========================================================================== */

// --- GLOBAL APPLICATION STATE ---
const state = {
    playerName: 'Lucky Gambler',
    chips: 1000,
    activeBet: 50,
    gameState: 'lobby', // 'lobby', 'betting', 'preflop', 'flop', 'river', 'showdown'
    playerCards: [],
    computerCards: [],
    communityCards: [],
    stats: {
        total_games: 0,
        player_wins: 0,
        computer_wins: 0,
        pushes: 0,
        total_chips: 1000,
        longest_streak: 0,
        best_hand: 'None',
        profit_loss: 0,
        last_100_total: 0,
        last_100_wins: 0,
        last_100_losses: 0,
        last_100_pushes: 0
    },
    soundEnabled: true
};

// --- SUIT & RANK SYMBOLS DICTIONARY ---
const SUIT_SYMBOLS = { 'S': '♠', 'H': '♥', 'D': '♦', 'C': '♣' };
const RANK_CHARS = {
    2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8', 9: '9',
    10: '10', 11: 'J', 12: 'Q', 13: 'K', 14: 'A'
};

// --- WEB AUDIO API SYNTHESIZER ---
const SoundSynth = {
    ctx: null,
    init() {
        if (!this.ctx) {
            this.ctx = new (window.AudioContext || window.webkitAudioContext)();
        }
        if (this.ctx.state === 'suspended') {
            this.ctx.resume();
        }
    },
    playWin() {
        if (!state.soundEnabled) return;
        this.init();
        const now = this.ctx.currentTime;
        this.beep(523.25, 0.08, now); // C5
        this.beep(659.25, 0.08, now + 0.08); // E5
        this.beep(783.99, 0.12, now + 0.16); // G5
        this.beep(1046.50, 0.28, now + 0.28); // C6
    },
    playLoss() {
        if (!state.soundEnabled) return;
        this.init();
        const now = this.ctx.currentTime;
        this.beep(392.00, 0.12, now); // G4
        this.beep(349.23, 0.12, now + 0.12); // F4
        this.beep(311.13, 0.35, now + 0.24); // Eb4
    },
    playPush() {
        if (!state.soundEnabled) return;
        this.init();
        const now = this.ctx.currentTime;
        this.beep(587.33, 0.15, now); // D5
        this.beep(587.33, 0.15, now + 0.2); // D5
    },
    playDeal() {
        if (!state.soundEnabled) return;
        this.init();
        this.beep(950, 0.04, this.ctx.currentTime, 'triangle', 0.08);
    },
    playClick() {
        if (!state.soundEnabled) return;
        this.init();
        this.beep(720, 0.02, this.ctx.currentTime, 'sine', 0.12);
    },
    playFlip() {
        if (!state.soundEnabled) return;
        this.init();
        this.beep(420, 0.06, this.ctx.currentTime, 'sine', 0.15);
    },
    beep(frequency, duration, time, type = 'sine', volume = 0.25) {
        const osc = this.ctx.createOscillator();
        const gainNode = this.ctx.createGain();
        osc.connect(gainNode);
        gainNode.connect(this.ctx.destination);
        
        osc.type = type;
        osc.frequency.setValueAtTime(frequency, time);
        
        gainNode.gain.setValueAtTime(volume, time);
        gainNode.gain.exponentialRampToValueAtTime(0.001, time + duration);
        
        osc.start(time);
        osc.stop(time + duration);
    }
};

// --- CANVAS CONFETTI PARTICLE SYSTEM ---
const Confetti = {
    canvas: null,
    ctx: null,
    particles: [],
    active: false,
    init() {
        if (this.canvas) return;
        this.canvas = document.getElementById('confetti-canvas');
        this.ctx = this.canvas.getContext('2d');
        window.addEventListener('resize', () => this.resize());
        this.resize();
    },
    resize() {
        if (!this.canvas) return;
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
    },
    start() {
        this.init();
        this.particles = [];
        this.active = true;
        const colors = ['#f39c12', '#2ecc71', '#3498db', '#e74c3c', '#9b59b6', '#e67e22'];
        for (let i = 0; i < 150; i++) {
            this.particles.push({
                x: Math.random() * this.canvas.width,
                y: Math.random() * this.canvas.height - this.canvas.height,
                r: Math.random() * 6 + 4,
                d: Math.random() * this.canvas.height,
                color: colors[Math.floor(Math.random() * colors.length)],
                tilt: Math.random() * 10 - 5,
                tiltAngleIncremental: Math.random() * 0.07 + 0.02,
                tiltAngle: 0
            });
        }
        this.animate();
    },
    stop() {
        this.active = false;
        if (this.ctx && this.canvas) {
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        }
    },
    animate() {
        if (!this.active) return;
        requestAnimationFrame(() => this.animate());
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        let remaining = false;
        for (let p of this.particles) {
            p.tiltAngle += p.tiltAngleIncremental;
            p.y += (Math.cos(p.d) + 3 + p.r / 2) / 2;
            p.x += Math.sin(p.tiltAngle);
            p.tilt = Math.sin(p.tiltAngle - p.r / 2) * 15;
            
            if (p.y <= this.canvas.height) {
                remaining = true;
            }
            
            this.ctx.beginPath();
            this.ctx.lineWidth = p.r;
            this.ctx.strokeStyle = p.color;
            this.ctx.moveTo(p.x + p.tilt + p.r / 2, p.y);
            this.ctx.lineTo(p.x + p.tilt, p.y + p.tilt + p.r / 2);
            this.ctx.stroke();
        }
        
        if (!remaining) {
            this.stop();
        }
    }
};

// --- AUDIT LOGGER ---
function logAudit(message) {
    const logArea = document.getElementById('audit-log-content');
    if (!logArea) return;
    const timestamp = new Date().toLocaleTimeString();
    logArea.innerHTML += `\n[${timestamp}] ${message}`;
    logArea.scrollTop = logArea.scrollHeight;
}

// --- CARD RENDERING HELPER ---
function renderHand(containerId, cards, faceUpArray) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';
    
    cards.forEach((card, index) => {
        const cardEl = document.createElement('div');
        // If it's a card back, we represent standard black suit for fallback
        const isRed = card.rank !== 0 && (card.suit === 'H' || card.suit === 'D');
        cardEl.className = `card ${isRed ? 'suit-red' : 'suit-black'}`;
        cardEl.dataset.index = index;
        
        // Structure front and back cards
        cardEl.innerHTML = `
            <div class="card-inner">
                <div class="card-front">
                    <div class="card-corner corner-top">
                        <span>${RANK_CHARS[card.rank] || ''}</span>
                        <span>${SUIT_SYMBOLS[card.suit] || ''}</span>
                    </div>
                    <div class="card-center-suit">${SUIT_SYMBOLS[card.suit] || ''}</div>
                    <div class="card-corner corner-bottom">
                        <span>${RANK_CHARS[card.rank] || ''}</span>
                        <span>${SUIT_SYMBOLS[card.suit] || ''}</span>
                    </div>
                </div>
                <div class="card-back">
                    <div class="card-back-pattern">
                        <span>🌌</span>
                        GRAVITY
                    </div>
                </div>
            </div>
        `;
        
        container.appendChild(cardEl);
        
        // Slide dealing effect
        setTimeout(() => {
            if (faceUpArray[index]) {
                cardEl.classList.add('flipped');
                if (state.soundEnabled) SoundSynth.playFlip();
            }
        }, index * 120 + 80);
        
        if (state.soundEnabled) {
            setTimeout(() => SoundSynth.playDeal(), index * 120);
        }
    });
}

// --- STATE AND DOM RENDERING ENGINE ---
function updateDOM() {
    // 1. Screens
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    if (state.gameState === 'lobby') {
        document.getElementById('lobby-screen').classList.add('active');
    } else {
        document.getElementById('game-screen').classList.add('active');
    }
    
    // 2. Chip labels
    document.getElementById('display-player-name').textContent = state.playerName;
    document.getElementById('display-chips').textContent = Number(state.chips).toLocaleString();
    document.getElementById('lbl-games-played').textContent = state.stats.total_games;
    document.getElementById('lbl-win-streak').textContent = state.stats.longest_streak;
    
    // 3. UI control states
    const betControls = document.getElementById('betting-controls');
    const streetControls = document.getElementById('street-controls');
    const commSection = document.getElementById('community-section');
    
    if (state.gameState === 'betting') {
        betControls.classList.add('active');
        streetControls.classList.remove('active');
        commSection.classList.add('hidden');
        
        document.getElementById('action-prompt').classList.remove('hidden');
        document.getElementById('action-prompt').textContent = "Place your bet amount to deal hole cards...";
        document.getElementById('showdown-results').classList.add('hidden');
        
        // Clear rankings badges
        document.getElementById('computer-hand-rank').classList.add('hidden');
        document.getElementById('player-hand-rank').classList.add('hidden');
        
        // Render neutral hands
        document.getElementById('computer-cards').innerHTML = '<div class="action-prompt">Dealer awaiting buy-in</div>';
        document.getElementById('player-cards').innerHTML = '<div class="action-prompt">Place bet to view hole cards</div>';
        
    } else if (state.gameState === 'preflop') {
        betControls.classList.remove('active');
        streetControls.classList.add('active');
        commSection.classList.remove('hidden');
        document.getElementById('action-prompt').classList.add('hidden');
        document.getElementById('showdown-results').classList.add('hidden');
        
        // Update Flop Street UI
        document.getElementById('street-title').textContent = "Round 2: The Flop";
        document.getElementById('street-subtitle').textContent = "Optionally bet more chips (minimum 10) or Check (0) to deal the Flop.";
        document.getElementById('street-bet-input').value = 0;
        document.getElementById('btn-street-action').textContent = "CHECK / DEAL FLOP";
        
    } else if (state.gameState === 'flop') {
        betControls.classList.remove('active');
        streetControls.classList.add('active');
        commSection.classList.remove('hidden');
        document.getElementById('action-prompt').classList.add('hidden');
        document.getElementById('showdown-results').classList.add('hidden');
        
        // Update River Street UI
        document.getElementById('street-title').textContent = "Round 3: The River";
        document.getElementById('street-subtitle').textContent = "Optionally bet more chips (minimum 10) or Check (0) to deal the Turn & River.";
        document.getElementById('street-bet-input').value = 0;
        document.getElementById('btn-street-action').textContent = "CHECK / DEAL RIVER";
        
    } else if (state.gameState === 'river') {
        betControls.classList.remove('active');
        streetControls.classList.add('active');
        commSection.classList.remove('hidden');
        document.getElementById('action-prompt').classList.add('hidden');
        document.getElementById('showdown-results').classList.add('hidden');
        
        // Update Showdown UI
        document.getElementById('street-title').textContent = "Showdown Phase";
        document.getElementById('street-subtitle').textContent = "Board completed. Click Showdown to reveal dealer's hole cards and evaluate.";
        document.getElementById('street-bet-input').value = 0;
        document.getElementById('btn-street-action').textContent = "REVEAL SHOWDOWN";
        
    } else if (state.gameState === 'showdown') {
        betControls.classList.remove('active');
        streetControls.classList.remove('active');
        commSection.classList.remove('hidden');
        document.getElementById('action-prompt').classList.add('hidden');
    }
}

// --- REST API BACKEND INTERACTIONS ---

// 1. Enter Casino lobby
async function handleLogin() {
    SoundSynth.playClick();
    const nameInput = document.getElementById('player-name-input').value.trim();
    if (!nameInput) return;
    
    state.playerName = nameInput;
    logAudit(`Connecting to session... User verified: ${nameInput}`);
    
    try {
        const res = await fetch('/api/select_player', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ player_name: nameInput })
        });
        const data = await res.json();
        
        state.chips = data.total_chips;
        state.gameState = 'betting';
        
        await fetchStats();
        updateDOM();
        logAudit(`Database initialized. Current chips balance loaded: ${state.chips}`);
    } catch (e) {
        logAudit(`Connection Error: ${e.message}`);
    }
}

// 2. Deal/Place Bet (Preflop street)
async function handleDeal() {
    SoundSynth.playClick();
    const betVal = parseInt(document.getElementById('bet-input').value);
    if (isNaN(betVal) || betVal < 10) {
        logAudit("Wager failed: Minimum bet is 10 chips.");
        return;
    }
    if (betVal > state.chips) {
        logAudit("Wager failed: Insufficient chips.");
        return;
    }
    
    state.activeBet = betVal;
    logAudit(`Transaction pending: Placing wager of ${betVal} chips...`);
    
    try {
        const res = await fetch('/api/place_bet', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ bet: betVal })
        });
        const data = await res.json();
        
        if (data.error) {
            logAudit(`Wager declined by server: ${data.error}`);
            if (data.reloaded) {
                state.chips = 1000;
                updateDOM();
            }
            return;
        }
        
        state.playerCards = data.player_hand;
        state.computerCards = data.computer_hand; // Placeholder card backs
        state.communityCards = [];
        state.gameState = 'preflop';
        state.chips = data.current_chips;
        state.activeBet = data.total_bet;
        
        updateDOM();
        logAudit(`Hole cards dealt. Active wagers: ${state.activeBet} chips.`);
        
        // Render 2 cards each
        renderHand('computer-cards', state.computerCards, [false, false]);
        renderHand('player-cards', state.playerCards, [true, true]);
        
        // Render 5 empty card outlines in community board
        const emptyCommunity = [
            { rank: 0, suit: 'S' }, { rank: 0, suit: 'S' }, { rank: 0, suit: 'S' },
            { rank: 0, suit: 'S' }, { rank: 0, suit: 'S' }
        ];
        renderHand('community-cards', emptyCommunity, [false, false, false, false, false]);
        
    } catch (e) {
        logAudit(`Transaction failed: ${e.message}`);
    }
}

// 3. Multi-street Action (Flop betting, River betting, Showdown)
async function handleStreetAction() {
    SoundSynth.playClick();
    const streetBetInput = document.getElementById('street-bet-input');
    const streetBet = parseInt(streetBetInput.value) || 0;
    
    if (streetBet > 0) {
        if (streetBet < 10) {
            logAudit("Wager failed: Minimum bet is 10 chips.");
            return;
        }
        if (streetBet > state.chips) {
            logAudit("Wager failed: Insufficient chips.");
            return;
        }
    }
    
    if (state.gameState === 'preflop') {
        logAudit(`Flop Street wagers: adding ${streetBet} chips...`);
        try {
            const res = await fetch('/api/deal_flop', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ add_bet: streetBet })
            });
            const data = await res.json();
            
            if (data.error) {
                logAudit(`Wager declined by server: ${data.error}`);
                return;
            }
            
            state.gameState = 'flop';
            state.activeBet = data.total_bet;
            state.chips = data.current_chips;
            state.communityCards = data.community_cards; // Contains first 3 cards (Flop)
            
            updateDOM();
            logAudit(`Flop dealt. Community cards updated. Active wagers: ${state.activeBet} chips.`);
            
            // Render 3 flop cards face-up + 2 backs
            const flopRenderList = [
                state.communityCards[0], state.communityCards[1], state.communityCards[2],
                { rank: 0, suit: 'S' }, { rank: 0, suit: 'S' }
            ];
            renderHand('community-cards', flopRenderList, [true, true, true, false, false]);
            
        } catch (e) {
            logAudit(`Flop Deal Action failed: ${e.message}`);
        }
        
    } else if (state.gameState === 'flop') {
        logAudit(`River Street wagers: adding ${streetBet} chips...`);
        try {
            const res = await fetch('/api/deal_river', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ add_bet: streetBet })
            });
            const data = await res.json();
            
            if (data.error) {
                logAudit(`Wager declined by server: ${data.error}`);
                return;
            }
            
            state.gameState = 'river';
            state.activeBet = data.total_bet;
            state.chips = data.current_chips;
            state.communityCards = data.community_cards; // Contains all 5 cards
            
            updateDOM();
            logAudit(`River dealt. Community cards completed. Active wagers: ${state.activeBet} chips.`);
            
            // Render all 5 cards face-up
            renderHand('community-cards', state.communityCards, [true, true, true, true, true]);
            
        } catch (e) {
            logAudit(`River Deal Action failed: ${e.message}`);
        }
        
    } else if (state.gameState === 'river') {
        logAudit("Showdown pending: Evaluating hands...");
        try {
            const res = await fetch('/api/showdown', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
            const data = await res.json();
            
            if (data.error) {
                logAudit(`Showdown declined by server: ${data.error}`);
                return;
            }
            
            state.gameState = 'showdown';
            state.computerCards = data.computer_hand; // Revealed dealer hole cards
            state.chips = data.active_chips;
            
            updateDOM();
            
            // Render final showdown (Dealer hole cards flipped)
            renderHand('computer-cards', state.computerCards, [true, true]);
            
            // Display hand rankings badges
            const compRankBadge = document.getElementById('computer-hand-rank');
            compRankBadge.textContent = data.computer_rank;
            compRankBadge.classList.remove('hidden');
            
            const playerRankBadge = document.getElementById('player-hand-rank');
            playerRankBadge.textContent = data.player_rank;
            playerRankBadge.classList.remove('hidden');
            
            // Populate results card
            const resultsEl = document.getElementById('showdown-results');
            const headlineEl = document.getElementById('showdown-headline');
            const detailsEl = document.getElementById('showdown-details');
            const changeEl = document.getElementById('showdown-chips-change');
            
            resultsEl.className = `showdown-card glass-card ${data.winner}`;
            
            if (data.winner === 'player') {
                headlineEl.textContent = '🎉 YOU WIN! 🎉';
                changeEl.textContent = `${data.chips_change} Chips`;
                SoundSynth.playWin();
                Confetti.start();
            } else if (data.winner === 'computer') {
                headlineEl.textContent = '💸 COMPUTER WINS 💸';
                changeEl.textContent = `${data.chips_change} Chips`;
                SoundSynth.playLoss();
            } else {
                headlineEl.textContent = '🤝 PUSH (TIE) 🤝';
                changeEl.textContent = 'Returned';
                SoundSynth.playPush();
            }
            
            detailsEl.textContent = `${data.player_rank} vs ${data.computer_rank}`;
            resultsEl.classList.remove('hidden');
            
            logAudit(`--- SHOWDOWN AUDIT ---`);
            logAudit(`Outcome: ${data.winner.toUpperCase()} | Chips balance updated: ${state.chips}`);
            
            await fetchStats();
            
        } catch (e) {
            logAudit(`Showdown Action failed: ${e.message}`);
        }
    }
}

// 4. Handle Fold Action
async function handleFold() {
    SoundSynth.playClick();
    logAudit("Player chose to fold...");
    try {
        const res = await fetch('/api/fold', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await res.json();
        
        if (data.error) {
            logAudit(`Fold declined by server: ${data.error}`);
            return;
        }
        
        state.gameState = 'showdown';
        state.computerCards = data.computer_hand; // Revealed dealer hole cards
        state.chips = data.active_chips;
        
        updateDOM();
        
        // Render final showdown (Dealer hole cards flipped)
        renderHand('computer-cards', state.computerCards, [true, true]);
        
        // Display hand rankings badges
        const compRankBadge = document.getElementById('computer-hand-rank');
        compRankBadge.textContent = data.computer_rank;
        compRankBadge.classList.remove('hidden');
        
        const playerRankBadge = document.getElementById('player-hand-rank');
        playerRankBadge.textContent = data.player_rank;
        playerRankBadge.classList.remove('hidden');
        
        // Populate results card
        const resultsEl = document.getElementById('showdown-results');
        const headlineEl = document.getElementById('showdown-headline');
        const detailsEl = document.getElementById('showdown-details');
        const changeEl = document.getElementById('showdown-chips-change');
        
        resultsEl.className = `showdown-card glass-card ${data.winner}`;
        
        headlineEl.textContent = 'YOU FOLDED!';
        changeEl.textContent = `${data.chips_change} Chips`;
        SoundSynth.playLoss();
        
        detailsEl.textContent = `${data.player_rank} vs ${data.computer_rank}`;
        resultsEl.classList.remove('hidden');
        
        logAudit(`--- SHOWDOWN AUDIT ---`);
        logAudit(`Outcome: PLAYER FOLDED | Chips balance updated: ${state.chips}`);
        
        await fetchStats();
        
    } catch (e) {
        logAudit(`Fold Action failed: ${e.message}`);
    }
}

// 5. Fetch Stats from DB
async function fetchStats() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        
        state.stats = data;
        
        // Populate dashboard fields
        document.getElementById('stat-chips-pl').textContent = (data.profit_loss >= 0 ? '+' : '') + data.profit_loss;
        document.getElementById('stat-chips-pl').className = `stat-highlight ${data.profit_loss >= 0 ? 'seg-win' : 'seg-loss'}`;
        
        const decisive = data.player_wins + data.computer_wins;
        const rate = decisive > 0 ? (data.player_wins / decisive * 100) : 50.0;
        document.getElementById('stat-win-rate').textContent = `${rate.toFixed(1)}%`;
        
        document.getElementById('stat-best-hand').textContent = data.best_hand;
        document.getElementById('stat-max-streak').textContent = data.longest_streak;
        
        // Ratio Segment Bar
        const barWins = document.getElementById('bar-wins');
        const barPushes = document.getElementById('bar-pushes');
        const barLosses = document.getElementById('bar-losses');
        
        const total = data.total_games;
        if (total > 0) {
            barWins.style.width = `${(data.player_wins / total * 100)}%`;
            barWins.textContent = `Wins: ${data.player_wins}`;
            barPushes.style.width = `${(data.pushes / total * 100)}%`;
            barPushes.textContent = `Ties: ${data.pushes}`;
            barLosses.style.width = `${(data.computer_wins / total * 100)}%`;
            barLosses.textContent = `Losses: ${data.computer_wins}`;
        } else {
            barWins.style.width = '33%';
            barWins.textContent = 'Wins: 0';
            barPushes.style.width = '33%';
            barPushes.textContent = 'Ties: 0';
            barLosses.style.width = '34%';
            barLosses.textContent = 'Losses: 0';
        }
        
        // Luck Meter UI Gauge
        const decLast100 = data.last_100_wins + data.last_100_losses;
        const rateLast100 = decLast100 > 0 ? (data.last_100_wins / decLast100 * 100) : 50.0;
        
        const statusEl = document.getElementById('lbl-luck-meter-status');
        const fillEl = document.getElementById('luck-meter-fill');
        
        fillEl.style.width = `${rateLast100}%`;
        
        if (rateLast100 > 50.0) {
            statusEl.textContent = `Lucky! 🍀 (${rateLast100.toFixed(1)}% Win Rate over last ${decLast100} decisive hands)`;
            statusEl.style.color = 'var(--success)';
        } else if (rateLast100 < 50.0) {
            statusEl.textContent = `Cold... 🍂 (${rateLast100.toFixed(1)}% Win Rate over last ${decLast100} decisive hands)`;
            statusEl.style.color = 'var(--danger)';
        } else {
            statusEl.textContent = `Balanced ⚖️ (50.0% Win Rate over last ${decLast100} decisive hands)`;
            statusEl.style.color = 'var(--primary)';
        }
        
    } catch (e) {
        logAudit(`Stats Sync Error: ${e.message}`);
    }
}

// 5. Reset stats database
async function handleResetStats() {
    if (!confirm("Are you sure you want to reset all profile stats? This will wipe your history and set chips to 1,000.")) return;
    
    try {
        const res = await fetch('/api/reset', { method: 'POST' });
        const data = await res.json();
        
        state.chips = 1000;
        state.gameState = 'betting';
        
        logAudit("Database has been reset. Fresh start initiated.");
        await fetchStats();
        updateDOM();
        
    } catch (e) {
        logAudit(`Database reset failed: ${e.message}`);
    }
}

// --- UI INTERACTIONS & EVENT BINDINGS ---
document.addEventListener('DOMContentLoaded', () => {
    // 1. Lobby Button
    document.getElementById('start-game-btn').addEventListener('click', handleLogin);
    document.getElementById('player-name-input').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') handleLogin();
    });
    
    // 2. Deal Button (Initial buy-in)
    document.getElementById('btn-deal').addEventListener('click', handleDeal);
    
    // 3. Street Multi-action Button
    document.getElementById('btn-street-action').addEventListener('click', handleStreetAction);
    document.getElementById('btn-fold').addEventListener('click', handleFold);
    
    // 4. Next Hand Button
    document.getElementById('btn-next-hand').addEventListener('click', () => {
        SoundSynth.playClick();
        Confetti.stop();
        state.gameState = 'betting';
        updateDOM();
    });
    
    // 5. Dashboard modal interactions
    const overlay = document.getElementById('dashboard-overlay');
    document.getElementById('btn-show-dashboard').addEventListener('click', () => {
        SoundSynth.playClick();
        overlay.classList.add('active');
    });
    document.getElementById('btn-close-dashboard').addEventListener('click', () => {
        SoundSynth.playClick();
        overlay.classList.remove('active');
    });
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            SoundSynth.playClick();
            overlay.classList.remove('active');
        }
    });
    
    // 6. Reset Button
    document.getElementById('btn-reset-stats').addEventListener('click', handleResetStats);
    
    // 7. Toggle Audit log window
    document.getElementById('btn-toggle-audit-logs').addEventListener('click', () => {
        SoundSynth.playClick();
        const logWindow = document.getElementById('audit-log-window');
        const btn = document.getElementById('btn-toggle-audit-logs');
        if (logWindow.classList.contains('hidden')) {
            logWindow.classList.remove('hidden');
            btn.textContent = '🛠️ Hide Debug Provable Fair Log';
        } else {
            logWindow.classList.add('hidden');
            btn.textContent = '🛠️ Open Debug Provable Fair Log';
        }
    });
    
    // 8. Quit Button
    document.getElementById('btn-quit').addEventListener('click', () => {
        SoundSynth.playClick();
        if (confirm("Are you sure you want to exit the casino? Your current state will be saved.")) {
            state.gameState = 'lobby';
            updateDOM();
            logAudit("Quit casino session. Current balance persisted.");
        }
    });
    
    // 9. Sound Toggle Button
    document.getElementById('btn-sound-toggle').addEventListener('click', () => {
        state.soundEnabled = !state.soundEnabled;
        const btn = document.getElementById('btn-sound-toggle');
        btn.textContent = state.soundEnabled ? '🔊' : '🔇';
        SoundSynth.playClick();
    });
    
    // 10. Initial buy-in chip buttons
    document.querySelectorAll('.chip-btn:not(.street-chip)').forEach(btn => {
        btn.addEventListener('click', () => {
            SoundSynth.playClick();
            const val = parseInt(btn.dataset.value);
            const betInput = document.getElementById('bet-input');
            betInput.value = val;
        });
    });

    // 11. Street bet chip buttons
    document.querySelectorAll('.street-chip').forEach(btn => {
        btn.addEventListener('click', () => {
            SoundSynth.playClick();
            const val = parseInt(btn.dataset.value);
            const streetBetInput = document.getElementById('street-bet-input');
            streetBetInput.value = val;
        });
    });
});
