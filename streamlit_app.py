import streamlit as st
import time
from gravity_poker import Database, Deck, HandEvaluator, Card

# Page Config
st.set_page_config(page_title="Gravity Flip Poker", layout="wide", page_icon="🎲")

# Custom CSS for dark theme vibe
st.markdown("""
    <style>
        .stApp { background-color: #070913; color: white; }
        .card-container { display: flex; gap: 10px; margin-bottom: 20px; }
        .poker-card {
            background: linear-gradient(135deg, #ffffff 0%, #f4f5f8 100%);
            border-radius: 8px; width: 80px; height: 110px;
            display: flex; flex-direction: column; justify-content: space-between;
            padding: 5px; color: black; text-align: center; font-weight: bold;
            box-shadow: 0 4px 10px rgba(0,0,0,0.5);
        }
        .poker-card.red { color: #ff3b30; }
        .poker-card.black { color: #1c1c1e; }
        .card-center { font-size: 2rem; }
        .card-back {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: #f39c12; align-items: center; justify-content: center;
        }
    </style>
""", unsafe_allow_html=True)

# Initialize Session State
if 'db' not in st.session_state:
    st.session_state.db = Database()
if 'player_id' not in st.session_state:
    st.session_state.player_id = None
if 'game_state' not in st.session_state:
    st.session_state.game_state = 'login' # login, betting, showdown

def get_card_html(card, face_up=True):
    if not face_up:
        return '<div class="poker-card card-back">🌌<br>GRAVITY</div>'
    
    syms = {'S': '♠', 'H': '♥', 'D': '♦', 'C': '♣'}
    ranks = {11:'J', 12:'Q', 13:'K', 14:'A'}
    r = ranks.get(card.rank, str(card.rank))
    color = "red" if card.suit in ['H', 'D'] else "black"
    
    return f"""
    <div class="poker-card {color}">
        <div>{r}{syms[card.suit]}</div>
        <div class="card-center">{syms[card.suit]}</div>
        <div style="transform: rotate(180deg);">{r}{syms[card.suit]}</div>
    </div>
    """

st.title("🎲 Gravity Flip Poker - Pure Python Web App")

# Login Phase
if st.session_state.game_state == 'login':
    st.subheader("Welcome to the Casino")
    player_name = st.text_input("Enter Player Name:", "Lucky Gambler")
    if st.button("Join Table"):
        player = st.session_state.db.get_or_create_player(player_name)
        st.session_state.player_id = player['player_id']
        st.session_state.chips = player['total_chips']
        st.session_state.game_state = 'betting'
        st.rerun()

# Betting / Game Phase
elif st.session_state.game_state == 'betting':
    st.sidebar.header(f"💰 Balance: {st.session_state.chips} Chips")
    
    bet = st.number_input("Place your wager:", min_value=10, max_value=st.session_state.chips, value=50, step=10)
    
    if st.button("Deal Hand (Play to Showdown)"):
        if bet > st.session_state.chips:
            st.error("Insufficient chips!")
        else:
            st.session_state.chips -= bet
            st.session_state.current_bet = bet
            
            deck = Deck()
            deck.shuffle()
            st.session_state.player_hand = deck.draw(2)
            st.session_state.computer_hand = deck.draw(2)
            st.session_state.community_cards = deck.draw(5)
            
            st.session_state.game_state = 'showdown'
            st.rerun()

# Showdown Phase
elif st.session_state.game_state == 'showdown':
    st.sidebar.header(f"💰 Balance: {st.session_state.chips} Chips")
    st.subheader("Showdown Results")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("### Dealer Cards")
        cards_html = "".join([get_card_html(c) for c in st.session_state.computer_hand])
        st.markdown(f'<div class="card-container">{cards_html}</div>', unsafe_allow_html=True)
        
    with col2:
        st.markdown("### Community Cards")
        cards_html = "".join([get_card_html(c) for c in st.session_state.community_cards])
        st.markdown(f'<div class="card-container">{cards_html}</div>', unsafe_allow_html=True)
        
    with col3:
        st.markdown("### Your Cards")
        cards_html = "".join([get_card_html(c) for c in st.session_state.player_hand])
        st.markdown(f'<div class="card-container">{cards_html}</div>', unsafe_allow_html=True)
        
    # Evaluate
    p_rank, p_score, p_desc = HandEvaluator.evaluate_7_cards(st.session_state.player_hand, st.session_state.community_cards)
    c_rank, c_score, c_desc = HandEvaluator.evaluate_7_cards(st.session_state.computer_hand, st.session_state.community_cards)
    
    st.info(f"**Dealer Rank:** {c_desc}  \n**Your Rank:** {p_desc}")
    
    winner = 'push'
    if p_score > c_score:
        st.success(f"🎉 YOU WIN! You won {st.session_state.current_bet * 2} chips.")
        st.session_state.chips += st.session_state.current_bet * 2
        winner = 'player'
    elif c_score > p_score:
        st.error(f"💸 DEALER WINS! You lost {st.session_state.current_bet} chips.")
        winner = 'computer'
    else:
        st.warning(f"🤝 PUSH! Tie game. Wager returned.")
        st.session_state.chips += st.session_state.current_bet
        
    # Save to DB
    st.session_state.db.update_chips_direct(st.session_state.player_id, st.session_state.chips)
    st.session_state.db.update_player_stats(st.session_state.player_id, winner, st.session_state.current_bet * 2 if winner == 'player' else (st.session_state.current_bet if winner == 'push' else 0))
    
    if st.button("Play Next Hand"):
        st.session_state.game_state = 'betting'
        st.rerun()
