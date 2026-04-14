Name: Aditya Singh Rawat
GitHub: xyz508
# Regex → Automata Converter

A web application that converts regular expressions into equivalent finite automata using **Thompson's Construction**. Built as a single-page application with zero dependencies.

## Live Demo

Open `index.html` in any modern browser. No build step, no server, no npm install.

## Features

### Core
- **Regex Parser** — Recursive descent parser supporting: concatenation, union (`|`), Kleene star (`*`), plus (`+`), optional (`?`), parentheses, and epsilon (`ε`)
- **Thompson's Construction** — Converts parsed regex AST into an ε-NFA with guaranteed correctness
- **Subset Construction** — Converts ε-NFA into an equivalent DFA (ε-closure + move operations)
- **Visual Automaton Display** — Force-directed graph layout rendered as SVG with start arrows, accept state markers, and labeled transitions

### Interactive
- **String Simulation** — Test any input string against the current automaton (NFA or DFA mode)
- **Step-by-Step Mode** — Walk through the automaton one character at a time, with active states highlighted
- **Transition Table** — Toggle a formal transition table showing δ for every state/symbol pair
- **View Switching** — Instantly toggle between ε-NFA and DFA views

### UI
- Example regex chips for quick testing
- Live statistics (states, transitions, alphabet size, accept states)
- Responsive layout (works on desktop and mobile)
- Keyboard shortcuts (Enter to convert/simulate)

## Supported Regex Syntax

| Syntax | Meaning | Example |
|--------|---------|---------|
| `a` | Literal character | `a` matches "a" |
| `ab` | Concatenation | `ab` matches "ab" |
| `a\|b` | Union (alternation) | `a\|b` matches "a" or "b" |
| `a*` | Kleene star (0 or more) | `a*` matches "", "a", "aa", ... |
| `a+` | One or more | `a+` matches "a", "aa", ... |
| `a?` | Optional (0 or 1) | `a?` matches "" or "a" |
| `(...)` | Grouping | `(ab)*` matches "", "ab", "abab", ... |
| `ε` | Empty string | `(a\|ε)b` matches "b" or "ab" |

## Algorithm Details

### Thompson's Construction
Each regex operator maps to a specific NFA fragment:
- **Character `a`**: Two states connected by transition on `a`
- **Concatenation `RS`**: Connect R's accept to S's start via ε
- **Union `R|S`**: New start with ε to both; both accepts ε to new accept
- **Kleene Star `R*`**: Loop via ε from accept back to start; bypass via ε

### Subset Construction (ε-NFA → DFA)
1. Compute ε-closure of NFA start state → DFA start
2. For each unmarked DFA state and each alphabet symbol, compute move + ε-closure
3. Mark DFA state as accepting if it contains any NFA accept state
4. Repeat until no unmarked states remain

## Project Structure

```
regex-to-automata/
├── index.html    # Complete application (HTML + CSS + JS)
└── README.md     # This file
```

## How to Run

```bash
# Option 1: Just open the file
open index.html

# Option 2: Local server (if needed for any reason)
python3 -m http.server 8000
# Then visit http://localhost:8000
```

## Technologies

- Vanilla JavaScript (ES6+)
- SVG for automaton rendering
- CSS Grid/Flexbox for layout
- Zero external dependencies

## Screenshots

Run the application and try these examples:
- `(a|b)*abb` — Classic NFA exercise
- `(0|1)*10` — Binary strings ending in 10
- `a(a|b)*b` — Strings starting with a, ending with b

## License

MIT
