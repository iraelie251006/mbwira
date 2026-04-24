"""
USSD menu tree for Mbwira.

Constraints we design around:
- Each screen must be <= 182 characters (GSM-7 USSD limit).
- Session times out after ~30s; keep menus short.
- Users enter digits only. No free text on USSD.
- Users can drill down or type '0' to go back.

The tree is a dict of (state, language) -> dict with:
  - 'prompt': the screen text
  - 'type': 'CON' (continue) or 'END' (close session)
  - 'options': {input_digit: next_state}

IMPORTANT: The Kinyarwanda strings below are a first draft. Before going live,
they MUST be reviewed by a native speaker AND a licensed clinician.
"""
from typing import Literal

Language = Literal["rw", "en"]

# ---- Shared building blocks ----
BACK = "0"
EMERGENCY_SCREEN = "emergency"
COUNSELOR_SCREEN = "counselor_request"

# ---- TREE ----
# Each leaf either ends the session with 'END' or loops back via options.

TREE: dict[str, dict[str, dict]] = {
    # -------- ROOT --------
    "start": {
        "rw": {
            "type": "CON",
            "prompt": (
                "Murakaza neza kuri Mbwira.\n"
                "Ibanga ryawe riringanijwe.\n"
                "1. Ubuzima bw'imyororokere\n"
                "2. Ubuzima bwo mu mutwe\n"
                "3. Vugana n'umujyanama\n"
                "4. Ihutirwa (112)\n"
                "9. English"
            ),
            "options": {
                "1": "srh_menu",
                "2": "mh_menu",
                "3": COUNSELOR_SCREEN,
                "4": EMERGENCY_SCREEN,
                "9": "start_en",
            },
        },
        "en": {
            "type": "CON",
            "prompt": (
                "Welcome to Mbwira.\n"
                "Your privacy is protected.\n"
                "1. Sexual & reproductive health\n"
                "2. Mental health\n"
                "3. Talk to a counselor\n"
                "4. Emergency (112)\n"
                "9. Kinyarwanda"
            ),
            "options": {
                "1": "srh_menu",
                "2": "mh_menu",
                "3": COUNSELOR_SCREEN,
                "4": EMERGENCY_SCREEN,
                "9": "start",
            },
        },
    },

    # -------- SRH branch --------
    "srh_menu": {
        "rw": {
            "type": "CON",
            "prompt": (
                "Ubuzima bw'imyororokere:\n"
                "1. Kuboneza urubyaro\n"
                "2. Gutwita\n"
                "3. SIDA n'indwara\n"
                "4. Imihango\n"
                "5. Kwemeranya (consent)\n"
                "0. Subira inyuma"
            ),
            "options": {
                "1": "srh_contraception",
                "2": "srh_pregnancy",
                "3": "srh_hiv",
                "4": "srh_menstruation",
                "5": "srh_consent",
                "0": "start",
            },
        },
        "en": {
            "type": "CON",
            "prompt": (
                "Sexual & reproductive health:\n"
                "1. Contraception\n"
                "2. Pregnancy\n"
                "3. HIV/STIs\n"
                "4. Menstruation\n"
                "5. Consent & relationships\n"
                "0. Back"
            ),
            "options": {
                "1": "srh_contraception",
                "2": "srh_pregnancy",
                "3": "srh_hiv",
                "4": "srh_menstruation",
                "5": "srh_consent",
                "0": "start_en",
            },
        },
    },

    "srh_contraception": {
        "rw": {
            "type": "CON",
            "prompt": (
                "Uburyo bwo kuboneza urubyaro buraboneka ku buntu mu bigo nderabuzima "
                "by'Akarere. Kondomu, ibinini, sindano, IUD.\n"
                "1. Menya byinshi\n"
                "3. Vugana n'umujyanama\n"
                "0. Subira"
            ),
            "options": {"1": "srh_contraception_more", "3": COUNSELOR_SCREEN, "0": "srh_menu"},
        },
        "en": {
            "type": "CON",
            "prompt": (
                "Contraception is free at your district health center. "
                "Options: condoms, pills, injection, IUD.\n"
                "1. Learn more\n"
                "3. Talk to counselor\n"
                "0. Back"
            ),
            "options": {"1": "srh_contraception_more", "3": COUNSELOR_SCREEN, "0": "srh_menu"},
        },
    },
    "srh_contraception_more": {
        "rw": {
            "type": "END",
            "prompt": (
                "Kondomu ikurinda SIDA n'inda. Ibinini bifatwa buri munsi. "
                "Sindano ni buri mezi 3. Jya ku kigo nderabuzima."
            ),
        },
        "en": {
            "type": "END",
            "prompt": (
                "Condoms prevent HIV and pregnancy. Pills: daily. "
                "Injection: every 3 months. Visit any health center free of charge."
            ),
        },
    },

    "srh_pregnancy": {
        "rw": {
            "type": "CON",
            "prompt": (
                "Niba ushidikanya ko utwite, genda ku kigo nderabuzima bapime ku buntu. "
                "Ntugire ubwoba.\n"
                "3. Vugana n'umujyanama\n"
                "0. Subira"
            ),
            "options": {"3": COUNSELOR_SCREEN, "0": "srh_menu"},
        },
        "en": {
            "type": "CON",
            "prompt": (
                "If you think you might be pregnant, go to a health center for a free test. "
                "You are not alone.\n"
                "3. Talk to counselor\n"
                "0. Back"
            ),
            "options": {"3": COUNSELOR_SCREEN, "0": "srh_menu"},
        },
    },

    "srh_hiv": {
        "rw": {
            "type": "CON",
            "prompt": (
                "Ipimishe SIDA ku buntu ku kigo nderabuzima. Niba ufite SIDA, "
                "imiti iraboneka ku buntu kandi ituma uba muzima.\n"
                "3. Vugana n'umujyanama\n"
                "0. Subira"
            ),
            "options": {"3": COUNSELOR_SCREEN, "0": "srh_menu"},
        },
        "en": {
            "type": "CON",
            "prompt": (
                "HIV testing is free at any health center. If positive, free ARV "
                "treatment lets you live a full, healthy life.\n"
                "3. Talk to counselor\n"
                "0. Back"
            ),
            "options": {"3": COUNSELOR_SCREEN, "0": "srh_menu"},
        },
    },

    "srh_menstruation": {
        "rw": {
            "type": "CON",
            "prompt": (
                "Imihango ni ibisanzwe. Iyo ububabare burenze cyangwa ntiyaza amezi 3, "
                "jya ku kigo nderabuzima.\n"
                "3. Vugana n'umujyanama\n"
                "0. Subira"
            ),
            "options": {"3": COUNSELOR_SCREEN, "0": "srh_menu"},
        },
        "en": {
            "type": "CON",
            "prompt": (
                "Periods are normal. If pain is severe or you miss 3 months, "
                "visit a health center.\n"
                "3. Talk to counselor\n"
                "0. Back"
            ),
            "options": {"3": COUNSELOR_SCREEN, "0": "srh_menu"},
        },
    },

    "srh_consent": {
        "rw": {
            "type": "CON",
            "prompt": (
                "Kwemeranya bisaba ko uwo muri kumwe mwese mwemeye ku bushake bwanyu. "
                "Niba wakorewe ihohoterwa, hamagara Isange 3029.\n"
                "3. Vugana n'umujyanama\n"
                "0. Subira"
            ),
            "options": {"3": COUNSELOR_SCREEN, "0": "srh_menu"},
        },
        "en": {
            "type": "CON",
            "prompt": (
                "Consent means both people freely agree. If you've been abused, "
                "call Isange One Stop Center: 3029.\n"
                "3. Talk to counselor\n"
                "0. Back"
            ),
            "options": {"3": COUNSELOR_SCREEN, "0": "srh_menu"},
        },
    },

    # -------- Mental Health branch --------
    "mh_menu": {
        "rw": {
            "type": "CON",
            "prompt": (
                "Ubuzima bwo mu mutwe:\n"
                "1. Guhangayika\n"
                "2. Agahinda kenshi\n"
                "3. Kubura ibitotsi\n"
                "4. Ibibazo by'umuryango\n"
                "5. Ibitekerezo byo kwiyahura\n"
                "0. Subira"
            ),
            "options": {
                "1": "mh_anxiety",
                "2": "mh_depression",
                "3": "mh_sleep",
                "4": "mh_family",
                "5": "mh_suicidal",
                "0": "start",
            },
        },
        "en": {
            "type": "CON",
            "prompt": (
                "Mental health:\n"
                "1. Stress & anxiety\n"
                "2. Feeling depressed\n"
                "3. Trouble sleeping\n"
                "4. Family problems\n"
                "5. Thoughts of self-harm\n"
                "0. Back"
            ),
            "options": {
                "1": "mh_anxiety",
                "2": "mh_depression",
                "3": "mh_sleep",
                "4": "mh_family",
                "5": "mh_suicidal",
                "0": "start_en",
            },
        },
    },

    "mh_anxiety": {
        "rw": {
            "type": "CON",
            "prompt": (
                "Guhangayika ni ibisanzwe. Gerageza guhumeka buhoro inshuro 5. "
                "Vugana n'uwo wizeye.\n"
                "3. Vugana n'umujyanama\n"
                "0. Subira"
            ),
            "options": {"3": COUNSELOR_SCREEN, "0": "mh_menu"},
        },
        "en": {
            "type": "CON",
            "prompt": (
                "Anxiety is common. Try: slow breaths x5, talk to someone you trust.\n"
                "3. Talk to counselor\n"
                "0. Back"
            ),
            "options": {"3": COUNSELOR_SCREEN, "0": "mh_menu"},
        },
    },

    "mh_depression": {
        "rw": {
            "type": "CON",
            "prompt": (
                "Agahinda gahoraho ni ikibazo gikemuka. Nta cyaha gifitanye. "
                "Umujyanama ashobora kugufasha.\n"
                "3. Vugana n'umujyanama\n"
                "0. Subira"
            ),
            "options": {"3": COUNSELOR_SCREEN, "0": "mh_menu"},
        },
        "en": {
            "type": "CON",
            "prompt": (
                "Ongoing sadness is treatable. It's not your fault. "
                "A counselor can help.\n"
                "3. Talk to counselor\n"
                "0. Back"
            ),
            "options": {"3": COUNSELOR_SCREEN, "0": "mh_menu"},
        },
    },

    "mh_sleep": {
        "rw": {
            "type": "CON",
            "prompt": (
                "Gerageza: genda kuryama mu gihe kimwe, oya telefone ijoro, "
                "oya kawa nyuma ya saa sita.\n"
                "3. Vugana n'umujyanama\n"
                "0. Subira"
            ),
            "options": {"3": COUNSELOR_SCREEN, "0": "mh_menu"},
        },
        "en": {
            "type": "CON",
            "prompt": (
                "Try: same bedtime daily, no phone at night, no coffee after noon.\n"
                "3. Talk to counselor\n"
                "0. Back"
            ),
            "options": {"3": COUNSELOR_SCREEN, "0": "mh_menu"},
        },
    },

    "mh_family": {
        "rw": {
            "type": "CON",
            "prompt": (
                "Ibibazo by'umuryango birakomeye ariko birakemuka. "
                "Umujyanama atekereza nawe inzira.\n"
                "3. Vugana n'umujyanama\n"
                "0. Subira"
            ),
            "options": {"3": COUNSELOR_SCREEN, "0": "mh_menu"},
        },
        "en": {
            "type": "CON",
            "prompt": (
                "Family problems are hard but solvable. A counselor can think "
                "through it with you.\n"
                "3. Talk to counselor\n"
                "0. Back"
            ),
            "options": {"3": COUNSELOR_SCREEN, "0": "mh_menu"},
        },
    },

    "mh_suicidal": {
        # Auto-escalation: this immediately triggers counselor handoff + emergency info.
        "rw": {
            "type": "END",
            "prompt": (
                "Urashoboye. Uri wenyine ariko si wenyine. "
                "Hamagara 114 nonaha - niba uri mu kaga, ubufasha buraboneka. "
                "Umujyanama azaguhamagara mu masaha 24."
            ),
            "triggers_escalation": "suicidal_ideation",
        },
        "en": {
            "type": "END",
            "prompt": (
                "You matter. You are not alone. Call 114 now — free, "
                "confidential help is available. A counselor will call you within 24h."
            ),
            "triggers_escalation": "suicidal_ideation",
        },
    },

    # -------- Counselor request --------
    COUNSELOR_SCREEN: {
        "rw": {
            "type": "END",
            "prompt": (
                "Yego. Umujyanama azaguhamagara mu masaha 24 "
                "kuri nimero itazwi. Murakoze."
            ),
            "triggers_escalation": "counselor_request",
        },
        "en": {
            "type": "END",
            "prompt": (
                "Thank you. A counselor will call you within 24h from "
                "a private number. You are doing the right thing."
            ),
            "triggers_escalation": "counselor_request",
        },
    },

    # -------- Emergency --------
    EMERGENCY_SCREEN: {
        "rw": {
            "type": "END",
            "prompt": (
                "Hamagara 112 (Polisi) cyangwa 114 (Ubuzima) ubu. "
                "Isange Center: 3029. Uri mu mutekano."
            ),
        },
        "en": {
            "type": "END",
            "prompt": (
                "Call 112 (Police) or 114 (Health) now. "
                "Isange Center: 3029. You are safe to seek help."
            ),
        },
    },
}


def resolve_state(state: str, lang: Language) -> dict:
    """Look up a screen, falling back to start on unknown state."""
    node = TREE.get(state) or TREE["start"]
    return node.get(lang) or node["en"]


def next_state(current_state: str, user_input: str, lang: Language) -> str:
    """Given current state and input, decide next state."""
    node = resolve_state(current_state, lang)
    options = node.get("options", {})
    return options.get(user_input.strip(), current_state)


def parse_ussd_input(text: str) -> list[str]:
    """Africa's Talking sends accumulated input like '1*2*3'. Parse into history."""
    if not text:
        return []
    return [p for p in text.split("*") if p]


def walk_tree(text: str, lang: Language = "rw") -> tuple[str, dict]:
    """
    Walk the tree from 'start' through all user inputs, return (final_state, screen).
    """
    inputs = parse_ussd_input(text)
    state = "start" if lang == "rw" else "start"
    for digit in inputs:
        state = next_state(state, digit, lang)
        # Language toggle is implicit — we detect on next hop
        if state == "start_en":
            lang = "en"
            state = "start"
        elif state == "start" and lang == "en":
            lang = "rw"
    screen = resolve_state(state, lang)
    return state, screen
