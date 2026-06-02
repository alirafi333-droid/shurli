import json
import asyncio
from pyodide.http import pyfetch
from pyodide.ffi import create_proxy
from js import document, window, setTimeout, Math

state = {
    'playerName': 'Lucky Gambler',
    'chips': 1000,
    'activeBet': 50,
    'gameState': 'lobby', # 'lobby', 'betting', 'preflop', 'flop', 'river', 'showdown'
    'playerCards': [],
    'computerCards': [],
    'communityCards': [],
    'stats': {
        'total_games': 0, 'player_wins': 0, 'computer_wins': 0, 'pushes': 0,
        'total_chips': 1000, 'longest_streak': 0, 'best_hand': 'None',
        'profit_loss': 0, 'last_100_total': 0, 'last_100_wins': 0,
        'last_100_losses': 0, 'last_100_pushes': 0
    },
    'soundEnabled': True
}

SUIT_SYMBOLS = { 'S': '♠', 'H': '♥', 'D': '♦', 'C': '♣' }
RANK_CHARS = {
    2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8', 9: '9',
    10: '10', 11: 'J', 12: 'Q', 13: 'K', 14: 'A', 0: ''
}

def log_audit(msg):
    log_area = document.getElementById('audit-log-content')
    if not log_area: return
    # Create simple timestamp manually
    import datetime
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    log_area.innerHTML += f"\n[{ts}] {msg}"
    log_area.scrollTop = log_area.scrollHeight

# --- AUDIO ---
class SoundSynth:
    ctx = None
    @classmethod
    def init(cls):
        if not cls.ctx:
            if hasattr(window, 'AudioContext'):
                cls.ctx = window.AudioContext.new()
            elif hasattr(window, 'webkitAudioContext'):
                cls.ctx = window.webkitAudioContext.new()
        if cls.ctx and cls.ctx.state == 'suspended':
            cls.ctx.resume()

    @classmethod
    def beep(cls, freq, duration, time, wave_type='sine', volume=0.25):
        if not cls.ctx: return
        osc = cls.ctx.createOscillator()
        gain = cls.ctx.createGain()
        osc.connect(gain)
        gain.connect(cls.ctx.destination)
        osc.type = wave_type
        osc.frequency.setValueAtTime(freq, time)
        gain.gain.setValueAtTime(volume, time)
        gain.gain.exponentialRampToValueAtTime(0.001, time + duration)
        osc.start(time)
        osc.stop(time + duration)

    @classmethod
    def play_click(cls):
        if not state['soundEnabled']: return
        cls.init()
        cls.beep(720, 0.02, cls.ctx.currentTime, 'sine', 0.12)

    @classmethod
    def play_deal(cls):
        if not state['soundEnabled']: return
        cls.init()
        cls.beep(950, 0.04, cls.ctx.currentTime, 'triangle', 0.08)
        
    @classmethod
    def play_flip(cls):
        if not state['soundEnabled']: return
        cls.init()
        cls.beep(420, 0.06, cls.ctx.currentTime, 'sine', 0.15)
        
    @classmethod
    def play_win(cls):
        if not state['soundEnabled']: return
        cls.init()
        now = cls.ctx.currentTime
        cls.beep(523.25, 0.08, now)
        cls.beep(659.25, 0.08, now + 0.08)
        cls.beep(783.99, 0.12, now + 0.16)
        cls.beep(1046.50, 0.28, now + 0.28)

    @classmethod
    def play_loss(cls):
        if not state['soundEnabled']: return
        cls.init()
        now = cls.ctx.currentTime
        cls.beep(392.00, 0.12, now)
        cls.beep(349.23, 0.12, now + 0.12)
        cls.beep(311.13, 0.35, now + 0.24)
        
    @classmethod
    def play_push(cls):
        if not state['soundEnabled']: return
        cls.init()
        now = cls.ctx.currentTime
        cls.beep(587.33, 0.15, now)
        cls.beep(587.33, 0.15, now + 0.2)

def set_timeout_proxy(func, delay):
    proxy = create_proxy(func)
    setTimeout(proxy, delay)

def render_hand(container_id, cards, face_up_array):
    container = document.getElementById(container_id)
    if not container: return
    container.innerHTML = ''
    
    for i, card in enumerate(cards):
        rank = card.get('rank', 0)
        suit = card.get('suit', 'S')
        is_red = rank != 0 and (suit == 'H' or suit == 'D')
        class_suit = 'suit-red' if is_red else 'suit-black'
        
        rank_char = RANK_CHARS.get(rank, '')
        suit_sym = SUIT_SYMBOLS.get(suit, '')
        
        html = f"""
            <div class="card-inner">
                <div class="card-front">
                    <div class="card-corner corner-top">
                        <span>{rank_char}</span>
                        <span>{suit_sym}</span>
                    </div>
                    <div class="card-center-suit">{suit_sym}</div>
                    <div class="card-corner corner-bottom">
                        <span>{rank_char}</span>
                        <span>{suit_sym}</span>
                    </div>
                </div>
                <div class="card-back">
                    <div class="card-back-pattern">
                        <span>🌌</span>
                        GRAVITY
                    </div>
                </div>
            </div>
        """
        
        card_el = document.createElement('div')
        card_el.className = f"card {class_suit}"
        card_el.setAttribute('data-index', str(i))
        card_el.innerHTML = html
        container.appendChild(card_el)
        
        def flip_card(el=card_el, fu=face_up_array[i]):
            if fu:
                el.classList.add('flipped')
                SoundSynth.play_flip()
                
        def play_deal_sound():
            SoundSynth.play_deal()
            
        set_timeout_proxy(flip_card, i * 120 + 80)
        if state['soundEnabled']:
            set_timeout_proxy(play_deal_sound, i * 120)


def update_dom():
    for s in document.querySelectorAll('.screen'):
        s.classList.remove('active')
        
    if state['gameState'] == 'lobby':
        document.getElementById('lobby-screen').classList.add('active')
    else:
        document.getElementById('game-screen').classList.add('active')
        
    document.getElementById('display-player-name').textContent = state['playerName']
    document.getElementById('display-chips').textContent = f"{int(state['chips']):,}"
    document.getElementById('lbl-games-played').textContent = str(state['stats'].get('total_games', 0))
    document.getElementById('lbl-win-streak').textContent = str(state['stats'].get('longest_streak', 0))
    
    bet_ctrl = document.getElementById('betting-controls')
    str_ctrl = document.getElementById('street-controls')
    comm_sec = document.getElementById('community-section')
    prompt = document.getElementById('action-prompt')
    results = document.getElementById('showdown-results')
    
    if state['gameState'] == 'betting':
        bet_ctrl.classList.add('active')
        str_ctrl.classList.remove('active')
        comm_sec.classList.add('hidden')
        prompt.classList.remove('hidden')
        prompt.textContent = "Place your bet amount to deal hole cards..."
        results.classList.add('hidden')
        document.getElementById('computer-hand-rank').classList.add('hidden')
        document.getElementById('player-hand-rank').classList.add('hidden')
        document.getElementById('computer-cards').innerHTML = '<div class="action-prompt">Dealer awaiting buy-in</div>'
        document.getElementById('player-cards').innerHTML = '<div class="action-prompt">Place bet to view hole cards</div>'
        
    elif state['gameState'] == 'preflop':
        bet_ctrl.classList.remove('active')
        str_ctrl.classList.add('active')
        comm_sec.classList.remove('hidden')
        prompt.classList.add('hidden')
        results.classList.add('hidden')
        document.getElementById('street-title').textContent = "Round 2: The Flop"
        document.getElementById('street-subtitle').textContent = "Optionally bet more chips (minimum 10) or Check (0) to deal the Flop."
        document.getElementById('street-bet-input').value = "0"
        document.getElementById('btn-street-action').textContent = "CHECK / DEAL FLOP"
        
    elif state['gameState'] == 'flop':
        bet_ctrl.classList.remove('active')
        str_ctrl.classList.add('active')
        comm_sec.classList.remove('hidden')
        prompt.classList.add('hidden')
        results.classList.add('hidden')
        document.getElementById('street-title').textContent = "Round 3: The River"
        document.getElementById('street-subtitle').textContent = "Optionally bet more chips (minimum 10) or Check (0) to deal the Turn & River."
        document.getElementById('street-bet-input').value = "0"
        document.getElementById('btn-street-action').textContent = "CHECK / DEAL RIVER"
        
    elif state['gameState'] == 'river':
        bet_ctrl.classList.remove('active')
        str_ctrl.classList.add('active')
        comm_sec.classList.remove('hidden')
        prompt.classList.add('hidden')
        results.classList.add('hidden')
        document.getElementById('street-title').textContent = "Showdown Phase"
        document.getElementById('street-subtitle').textContent = "Board completed. Click Showdown to reveal dealer's hole cards and evaluate."
        document.getElementById('street-bet-input').value = "0"
        document.getElementById('btn-street-action').textContent = "REVEAL SHOWDOWN"
        
    elif state['gameState'] == 'showdown':
        bet_ctrl.classList.remove('active')
        str_ctrl.classList.remove('active')
        comm_sec.classList.remove('hidden')
        prompt.classList.add('hidden')

async def fetch_stats():
    try:
        res = await pyfetch('/api/stats')
        data = await res.json()
        state['stats'] = dict(data)
        
        pl = data.get('profit_loss', 0)
        pl_str = f"+{pl}" if pl >= 0 else str(pl)
        document.getElementById('stat-chips-pl').textContent = pl_str
        document.getElementById('stat-chips-pl').className = f"stat-highlight {'seg-win' if pl >= 0 else 'seg-loss'}"
        
        pw = data.get('player_wins', 0)
        cw = data.get('computer_wins', 0)
        pu = data.get('pushes', 0)
        total = data.get('total_games', 0)
        
        decisive = pw + cw
        rate = (pw / decisive * 100) if decisive > 0 else 50.0
        document.getElementById('stat-win-rate').textContent = f"{rate:.1f}%"
        document.getElementById('stat-best-hand').textContent = data.get('best_hand', 'None')
        document.getElementById('stat-max-streak').textContent = str(data.get('longest_streak', 0))
        
        bar_w = document.getElementById('bar-wins')
        bar_p = document.getElementById('bar-pushes')
        bar_l = document.getElementById('bar-losses')
        
        if total > 0:
            bar_w.style.width = f"{(pw/total*100)}%"
            bar_w.textContent = f"Wins: {pw}"
            bar_p.style.width = f"{(pu/total*100)}%"
            bar_p.textContent = f"Ties: {pu}"
            bar_l.style.width = f"{(cw/total*100)}%"
            bar_l.textContent = f"Losses: {cw}"
        else:
            bar_w.style.width = '33%'
            bar_p.style.width = '33%'
            bar_l.style.width = '34%'
            bar_w.textContent = 'Wins: 0'
            bar_p.textContent = 'Ties: 0'
            bar_l.textContent = 'Losses: 0'
            
    except Exception as e:
        log_audit(f"Stats Error: {e}")

async def handle_login(e=None):
    SoundSynth.play_click()
    name_input = document.getElementById('player-name-input').value.strip()
    if not name_input: return
    
    state['playerName'] = name_input
    log_audit(f"Connecting to session... User verified: {name_input}")
    
    try:
        res = await pyfetch('/api/select_player', method='POST', headers={'Content-Type': 'application/json'}, body=json.dumps({'player_name': name_input}))
        data = await res.json()
        state['chips'] = data.get('total_chips', 1000)
        state['gameState'] = 'betting'
        await fetch_stats()
        update_dom()
        log_audit(f"Database initialized. Current chips: {state['chips']}")
    except Exception as err:
        log_audit(f"Connection Error: {err}")

async def handle_deal(e=None):
    SoundSynth.play_click()
    bet_val_str = document.getElementById('bet-input').value
    try:
        bet_val = int(bet_val_str)
    except:
        return
        
    if bet_val < 10:
        log_audit("Wager failed: Minimum bet is 10.")
        return
    if bet_val > state['chips']:
        log_audit("Wager failed: Insufficient chips.")
        return
        
    state['activeBet'] = bet_val
    log_audit(f"Placing wager of {bet_val} chips...")
    
    try:
        res = await pyfetch('/api/place_bet', method='POST', headers={'Content-Type': 'application/json'}, body=json.dumps({'bet': bet_val}))
        data = await res.json()
        
        if data.get('error'):
            log_audit(f"Error: {data['error']}")
            if data.get('reloaded'):
                state['chips'] = 1000
                update_dom()
            return
            
        state['playerCards'] = data['player_hand']
        state['computerCards'] = data['computer_hand']
        state['communityCards'] = []
        state['gameState'] = 'preflop'
        state['chips'] = data['current_chips']
        state['activeBet'] = data['total_bet']
        
        update_dom()
        render_hand('computer-cards', state['computerCards'], [False, False])
        render_hand('player-cards', state['playerCards'], [True, True])
        
        empty_comm = [{'rank':0,'suit':'S'} for _ in range(5)]
        render_hand('community-cards', empty_comm, [False]*5)
    except Exception as err:
        log_audit(f"Deal Error: {err}")

async def handle_street_action(e=None):
    SoundSynth.play_click()
    val_str = document.getElementById('street-bet-input').value
    try:
        street_bet = int(val_str)
    except:
        street_bet = 0
        
    if street_bet > 0:
        if street_bet < 10:
            log_audit("Wager failed: Minimum bet is 10.")
            return
        if street_bet > state['chips']:
            log_audit("Wager failed: Insufficient chips.")
            return
            
    gs = state['gameState']
    
    if gs == 'preflop':
        res = await pyfetch('/api/deal_flop', method='POST', headers={'Content-Type': 'application/json'}, body=json.dumps({'add_bet': street_bet}))
        data = await res.json()
        if data.get('error'): return
        state['gameState'] = 'flop'
        state['activeBet'] = data['total_bet']
        state['chips'] = data['current_chips']
        state['communityCards'] = data['community_cards']
        update_dom()
        
        render_list = state['communityCards'][:3] + [{'rank':0,'suit':'S'}, {'rank':0,'suit':'S'}]
        render_hand('community-cards', render_list, [True, True, True, False, False])
        
    elif gs == 'flop':
        res = await pyfetch('/api/deal_river', method='POST', headers={'Content-Type': 'application/json'}, body=json.dumps({'add_bet': street_bet}))
        data = await res.json()
        if data.get('error'): return
        state['gameState'] = 'river'
        state['activeBet'] = data['total_bet']
        state['chips'] = data['current_chips']
        state['communityCards'] = data['community_cards']
        update_dom()
        
        render_hand('community-cards', state['communityCards'], [True]*5)
        
    elif gs == 'river':
        res = await pyfetch('/api/showdown', method='POST', headers={'Content-Type': 'application/json'})
        data = await res.json()
        if data.get('error'): return
        state['gameState'] = 'showdown'
        state['computerCards'] = data['computer_hand']
        state['chips'] = data['active_chips']
        update_dom()
        
        render_hand('computer-cards', state['computerCards'], [True, True])
        
        c_badge = document.getElementById('computer-hand-rank')
        c_badge.textContent = data['computer_rank']
        c_badge.classList.remove('hidden')
        
        p_badge = document.getElementById('player-hand-rank')
        p_badge.textContent = data['player_rank']
        p_badge.classList.remove('hidden')
        
        res_el = document.getElementById('showdown-results')
        res_el.className = f"showdown-card glass-card {data['winner']}"
        
        head_el = document.getElementById('showdown-headline')
        change_el = document.getElementById('showdown-chips-change')
        
        if data['winner'] == 'player':
            head_el.textContent = '🎉 YOU WIN! 🎉'
            change_el.textContent = f"{data['chips_change']} Chips"
            SoundSynth.play_win()
        elif data['winner'] == 'computer':
            head_el.textContent = '💸 COMPUTER WINS 💸'
            change_el.textContent = f"{data['chips_change']} Chips"
            SoundSynth.play_loss()
        else:
            head_el.textContent = '🤝 PUSH (TIE) 🤝'
            change_el.textContent = 'Returned'
            SoundSynth.play_push()
            
        document.getElementById('showdown-details').textContent = f"{data['player_rank']} vs {data['computer_rank']}"
        res_el.classList.remove('hidden')
        
        await fetch_stats()

# Bindings
def bind_events():
    document.getElementById('start-game-btn').addEventListener('click', create_proxy(handle_login))
    document.getElementById('btn-deal').addEventListener('click', create_proxy(handle_deal))
    document.getElementById('btn-street-action').addEventListener('click', create_proxy(handle_street_action))
    
    def on_next_hand(e):
        SoundSynth.play_click()
        state['gameState'] = 'betting'
        update_dom()
    document.getElementById('btn-next-hand').addEventListener('click', create_proxy(on_next_hand))
    
    # Dashboard overlay
    dash = document.getElementById('dashboard-overlay')
    def show_dash(e): dash.classList.add('active')
    def hide_dash(e): dash.classList.remove('active')
    document.getElementById('btn-show-dashboard').addEventListener('click', create_proxy(show_dash))
    document.getElementById('btn-close-dashboard').addEventListener('click', create_proxy(hide_dash))
    
    # Chips
    def set_chip_val(val, target_id):
        SoundSynth.play_click()
        document.getElementById(target_id).value = str(val)
        
    for btn in document.querySelectorAll('.chip-btn:not(.street-chip)'):
        val = btn.getAttribute('data-value')
        btn.addEventListener('click', create_proxy(lambda e, v=val: set_chip_val(v, 'bet-input')))
        
    for btn in document.querySelectorAll('.street-chip'):
        val = btn.getAttribute('data-value')
        btn.addEventListener('click', create_proxy(lambda e, v=val: set_chip_val(v, 'street-bet-input')))

bind_events()
