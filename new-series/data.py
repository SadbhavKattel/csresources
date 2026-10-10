"""Content for three series. Facts checked 2026-10-10 against official pages where reachable
(see "source" on each item). Re-check deadlines before posting.

logo: key of assets/logos/<key>.png. Missing keys render as a name tile; drop the real logo
into logos/<key>.png and it is used instead.
"""

CLOSING_SOON = {
    "series": "closing soon",
    "accent": (255, 106, 77),
    "posts": [
        {
            "slug": "nsf-grfp",
            "cover": [("$37,000 a year.", "bold"), ("for 3 years.", "bold"), ("to do research.", "bold"),
                      None, ("applications close oct 20.", "regular")],
            "logo": "nsf", "logo_text": "NSF",
            "org": "National Science Foundation",
            "program": "Graduate Research Fellowship (GRFP)",
            "deadline": "Oct 20", "year": "2026",
            "deadline_note": "8 pm ET · computer science deadline · letters due Oct 16",
            "rows": [
                ("pays", "$37,000/yr stipend + $16,000/yr to your school, for 3 years"),
                ("where", "any accredited US grad school"),
                ("who can apply", "college seniors & first-year grad students · US citizens, nationals or permanent residents"),
            ],
            "link": "nsf.gov/funding/initiatives/grfp",
            "source": "https://www.nsf.gov/funding/initiatives/grfp/applicants/faq",
        },
        {
            "slug": "paul-daisy-soros",
            "cover": [("immigrant, or child of", "bold"), ("immigrants?", "bold"), ("$90,000 for grad school.", "bold"),
                      None, ("closes oct 29.", "regular")],
            "logo": "soros", "logo_text": "Soros",
            "org": "Paul & Daisy Soros Fellowships",
            "program": "Fellowships for New Americans",
            "deadline": "Oct 29", "year": "2026",
            "deadline_note": "2 pm ET · no exceptions",
            "rows": [
                ("pays", "up to $90,000 over 2 years: up to $25k/yr stipend + up to $20k/yr tuition"),
                ("where", "any US graduate or professional program, starting 2027"),
                ("who can apply", "immigrants & children of immigrants, age 30 or younger"),
            ],
            "link": "pdsoros.org",
            "source": "https://pdsoros-fellowships.smapply.io/",
        },
        {
            "slug": "hertz",
            "cover": [("a phd fellowship", "bold"), ("worth up to $250,000.", "bold"),
                      None, ("closes oct 30.", "regular")],
            "logo": "hertz", "logo_text": "Hertz",
            "org": "Hertz Foundation",
            "program": "Hertz Fellowship",
            "deadline": "Oct 30", "year": "2026",
            "deadline_note": "recommendation letters due Nov 2",
            "rows": [
                ("pays", "up to 5 years of PhD funding, valued up to $250,000"),
                ("where", "your PhD in applied science, engineering or math (CS counts)"),
                ("who can apply", "college seniors, gap-year & first-year grad students · US citizens or permanent residents"),
            ],
            "link": "hertzfoundation.org",
            "source": "https://www.hertzfoundation.org/hertz-fellowship/apply/",
        },
        {
            "slug": "daad-rise",
            "cover": [("spend next summer", "bold"), ("doing research in germany.", "bold"), ("they pay you.", "bold"),
                      None, ("closes nov 30.", "regular")],
            "logo": "daad", "logo_text": "DAAD",
            "org": "DAAD (German Academic Exchange Service)",
            "program": "RISE Germany 2027",
            "deadline": "Nov 30", "year": "2026",
            "deadline_note": "11:59 pm CET · recommendation letters due Dec 15",
            "rows": [
                ("pays", "€992/month stipend + insurance + travel subsidy"),
                ("where", "German universities & research institutes · ~3 months, summer 2027"),
                ("who can apply", "undergrads at North American, UK or Irish universities with 2+ years done · most spots need no German"),
            ],
            "link": "daad.de/rise",
            "source": "https://www.daad.de/rise/en/rise-germany/find-an-internship/what-applicants-need-to-know/",
        },
        {
            "slug": "doe-suli",
            "cover": [("intern at a national lab.", "bold"), ("$650 a week.", "bold"),
                      None, ("applications open oct 14.", "regular")],
            "logo": "doe", "logo_text": "DOE",
            "org": "U.S. Department of Energy",
            "program": "Science Undergraduate Laboratory Internships (SULI)",
            "deadline": "Jan 6", "year": "2027",
            "deadline_note": "opens Oct 14, 2026 · 5 pm ET · apply early",
            "rows": [
                ("pays", "$650/week stipend · some labs add housing help"),
                ("where", "DOE national labs across the US · 10 weeks, summer 2027"),
                ("who can apply", "full-time undergrads (community college too) or grads within 2 years · US citizens or permanent residents · 18+"),
            ],
            "link": "science.osti.gov/wdts/suli",
            "source": "https://science.osti.gov/wdts/suli/Key-Dates",
        },
    ],
}

PAID_TO_ATTEND = {
    "series": "they'll pay you to show up",
    "accent": (86, 211, 100),
    "posts": [
        {
            "slug": "kubecon-europe",
            "cover": [("kubecon can fly you", "bold"), ("to barcelona.", "bold"), ("for free.", "bold"),
                      None, ("here's how to apply.", "regular")],
            "logo": "kubernetes", "logo_text": "KubeCon",
            "event": "KubeCon + CloudNativeCon Europe",
            "where": "Barcelona, Spain", "when": "Mar 15–18, 2027",
            "covers": ["free ticket", "flights", "hotel", "airport rides"],
            "rows": [
                ("who can apply", "people who can't attend without help and aren't sponsored by an employer"),
                ("when to apply", "scholarship & travel-fund form opens late 2026 on the event site"),
            ],
            "link": "events.linuxfoundation.org",
            "source": "https://events.linuxfoundation.org/kubecon-cloudnativecon-europe/attend/scholarships-travel-funding/",
        },
        {
            "slug": "pycon-us",
            "cover": [("pycon will cover", "bold"), ("your flight and hotel.", "bold"),
                      None, ("if you apply in time.", "regular")],
            "logo": "python", "logo_text": "PyCon",
            "event": "PyCon US 2027",
            "sub": "travel grants",
            "where": "Long Beach, California", "when": "May 12–18, 2027",
            "covers": ["free ticket", "travel", "hotel"],
            "rows": [
                ("who can apply", "anyone who couldn't attend otherwise · grants are need-based"),
                ("when to apply", "last year: Dec 11 – Feb 25 · 2027 dates not posted yet"),
            ],
            "link": "us.pycon.org",
            "source": "https://us.pycon.org/2026/attend/faq/",
        },
        {
            "slug": "sigcse",
            "cover": [("free ticket to a", "bold"), ("cs conference.", "bold"),
                      None, ("all you do is volunteer.", "regular")],
            "logo": "acm", "logo_text": "SIGCSE",
            "event": "SIGCSE Technical Symposium 2027",
            "sub": "student volunteer program",
            "where": "Sacramento, California", "when": "Feb 17–20, 2027",
            "covers": ["free registration"],
            "rows": [
                ("who can apply", "undergrad or grad students, 18+"),
                ("when to apply", "student volunteer form opens around November 2026"),
                ("heads up", "covers your ticket, not travel. ask your department to fund the trip"),
            ],
            "link": "2027.sigcse-ts.acm.org",
            "source": "https://2027.sigcse-ts.acm.org/attending/Student+Volunteers",
        },
        {
            "slug": "tapia",
            "cover": [("a whole cs conference.", "bold"), ("hotel, meals, travel.", "bold"),
                      None, ("paid for.", "regular")],
            "logo": "tapia", "logo_text": "Tapia",
            "event": "Tapia Celebration of Diversity in Computing",
            "where": "2027 city TBA", "when": "usually September",
            "covers": ["registration", "hotel", "meals", "travel stipend"],
            "rows": [
                ("who can apply", "students at US colleges & universities"),
                ("when to apply", "last cycle closed Mar 3, 2026 · expect spring 2027"),
            ],
            "link": "tapiaconference.cmd-it.org",
            "source": "https://tapiaconference.cmd-it.org/call-for-participation/scholarships/",
        },
        {
            "slug": "linux-foundation",
            "cover": [("the linux foundation", "bold"), ("can pay for your trip.", "bold"),
                      None, ("to any of their events.", "regular")],
            "logo": "linuxfoundation", "logo_text": "Linux Foundation",
            "event": "Linux Foundation Travel Fund",
            "sub": "travel funding & registration scholarships",
            "where": "Open Source Summit, KubeCon & more", "when": "events all year, worldwide",
            "covers": ["free registration", "flights", "hotel", "airport rides"],
            "rows": [
                ("who can apply", "people from underrepresented groups, or who can't attend for financial reasons, with no company funding"),
                ("how", "each event's 'scholarships + travel funding' page"),
            ],
            "link": "events.linuxfoundation.org",
            "source": "https://events.linuxfoundation.org/open-source-summit-europe/attend/scholarships-travel-funding/",
        },
    ],
}

EDU_PERKS = {
    "series": "your .edu unlocks",
    "accent": (88, 166, 255),
    "posts": [
        {
            "slug": "coding-tools",
            "cover": [("your student email", "bold"), ("gets you every jetbrains ide.", "bold"),
                      None, ("free. and that's just one.", "regular")],
            "title": "free coding tools",
            "perks": [
                ("jetbrains", "JetBrains", "every IDE, free", "IntelliJ Ultimate, PyCharm, WebStorm & more · renew yearly while enrolled", "jetbrains.com/student"),
                ("frontendmasters", "Frontend Masters", "6 months free", "full course library · via GitHub Student Pack · no card", "frontendmasters.com"),
                ("namecheap", "Namecheap", "free .me domain, 1 year", "plus SSL · via GitHub Student Pack", "education.github.com/pack"),
            ],
        },
        {
            "slug": "cloud-credits",
            "cover": [("$612 in cloud credits.", "bold"), ("just for being a student.", "bold"),
                      None, ("most people never claim them.", "regular")],
            "title": "free cloud credits",
            "perks": [
                ("azure", "Microsoft Azure", "$100 credit, no card", "renews every year you're a full-time student · 18+", "azure.microsoft.com/free/students"),
                ("digitalocean", "DigitalOcean", "$200 credit", "valid 12 months · via GitHub Student Pack", "education.github.com/pack"),
                ("heroku", "Heroku", "$312 in credits", "$13/month for 24 months · via GitHub Student Pack", "heroku.com/students"),
            ],
        },
        {
            "slug": "design-tools",
            "cover": [("figma. autocad. unity.", "bold"), ("all free for students.", "bold"),
                      None, ("stop paying for them.", "regular")],
            "title": "free design & 3D tools",
            "perks": [
                ("figma", "Figma", "Professional plan, free", "verify you're a student · re-verify yearly", "figma.com/education"),
                ("autodesk", "Autodesk", "Fusion, AutoCAD, Maya free", "1-year access, renew while eligible", "autodesk.com/education"),
                ("unity", "Unity", "Student plan, free", "16+ at an accredited school", "unity.com/products"),
            ],
        },
        {
            "slug": "productivity",
            "cover": [("stop paying for notion.", "bold"),
                      None, ("3 tools that are free", "regular"), ("with your school email.", "regular")],
            "title": "free productivity tools",
            "perks": [
                ("notion", "Notion", "Plus plan, free", "sign up with your school email", "notion.com"),
                ("microsoft", "Microsoft 365", "Word, Excel, PowerPoint", "free web apps (Office 365 A1) with an eligible school email", "microsoft.com/education"),
                ("tableau", "Tableau", "Desktop + Prep, free", "1-year license, renew every year you're enrolled", "tableau.com/academic/students"),
            ],
        },
        {
            "slug": "claim-first",
            "cover": [("the student perk", "bold"), ("most people never claim.", "bold"),
                      None, ("it unlocks dozens more.", "regular")],
            "title": "claim these first",
            "perks": [
                ("github", "GitHub Student Pack", "dozens of free tools", "GitHub Pro + the Heroku, DigitalOcean, Namecheap & Frontend Masters offers", "education.github.com/pack"),
                ("gemini", "Google AI Pro", "12 months free (US)", "college students 18+ · redeem by Dec 31, 2026 · card needed, renews at $19.99/mo", "search: google ai pro students"),
                ("aws", "AWS Educate", "free cloud labs", "hands-on labs & badges · sign up with just an email, no card", "aws.amazon.com/education/awseducate"),
            ],
        },
    ],
}

SERIES = {"closing-soon": CLOSING_SOON, "paid-to-attend": PAID_TO_ATTEND, "edu-perks": EDU_PERKS}
