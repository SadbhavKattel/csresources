"""Posts for the "trust issues" series. Every bug here was run and confirmed.

cover:   lines on the cover, (text, weight); None = half-line gap
code:    the AI-written snippet shown on slide 2
diff:    slide 3's fix, as (sign, line) with sign "-", "+" or " "
explain: answer paragraphs; a paragraph starting with "$ " is drawn as code
"""

POSTS = [
    {
        "slug": "mutable-default",
        "lang": "python",
        "filename": "cart.py",
        "cover": [("ai wrote this python function.", "bold"), ("it works once.", "bold"),
                  ("then it doesn't.", "bold"), None, ("can you spot why?", "regular")],
        "question": "what does this print?",
        "code": '''def add_item(item, cart=[]):
    cart.append(item)
    return cart

a = add_item("apple")
b = add_item("milk")
print(a)''',
        "answer": "it prints ['apple', 'milk']",
        "explain": [
            "default arguments are created once, when the function is defined. not every time you call it.",
            "so every call without a cart shares the same list. a and b are literally the same object.",
        ],
        "fix_note": "use None as the default:",
        "diff": [("-", "def add_item(item, cart=[]):"),
                 ("+", "def add_item(item, cart=None):"),
                 ("+", "    if cart is None:"),
                 ("+", "        cart = []"),
                 (" ", "    cart.append(item)")],
    },
    {
        "slug": "remove-while-looping",
        "lang": "python",
        "filename": "filter.py",
        "cover": [('"remove the even numbers."', "bold"), ("ai's answer looks fine.", "bold"),
                  None, ("it isn't.", "regular")],
        "question": "what's left in nums?",
        "code": '''nums = [1, 2, 2, 3, 4]

for n in nums:
    if n % 2 == 0:
        nums.remove(n)

print(nums)''',
        "answer": "it prints [1, 2, 3]",
        "explain": [
            "removing an item while looping over the same list shifts everything after it one spot left.",
            "the loop keeps moving forward anyway, so the second 2 slides into a spot that was already checked and gets skipped.",
        ],
        "fix_note": "build a new list instead:",
        "diff": [("-", "for n in nums:"),
                 ("-", "    if n % 2 == 0:"),
                 ("-", "        nums.remove(n)"),
                 ("+", "nums = [n for n in nums if n % 2 != 0]")],
    },
    {
        "slug": "binary-search",
        "lang": "python",
        "filename": "search.py",
        "cover": [("ai's binary search", "bold"), ("passes most tests.", "bold"),
                  None, ("one input breaks it.", "regular")],
        "question": "find the bug.",
        "hint": "hint: try search([1, 3, 5], 5)",
        "code": '''def search(nums, target):
    lo, hi = 0, len(nums) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if nums[mid] == target:
            return mid
        if nums[mid] < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return -1''',
        "answer": "line 3 should be lo <= hi",
        "explain": [
            "with lo < hi the loop stops the moment lo and hi meet, so the last element left is never checked.",
            "search([1, 3, 5], 5) returns -1. so does search([7], 7).",
        ],
        "fix_note": "one character:",
        "diff": [("-", "    while lo < hi:"),
                 ("+", "    while lo <= hi:")],
    },
    {
        "slug": "async-foreach",
        "lang": "javascript",
        "filename": "orders.js",
        "cover": [("ai wrote this to total", "bold"), ("a user's orders.", "bold"),
                  None, ("it always returns 0.", "regular")],
        "question": "why does this return 0?",
        "code": '''async function getTotal(ids) {
  let total = 0;
  ids.forEach(async (id) => {
    const order = await fetchOrder(id);
    total += order.amount;
  });
  return total;
}''',
        "answer": "forEach doesn't wait for async callbacks",
        "explain": [
            "forEach starts every callback and moves on immediately. it ignores the promises they return.",
            "so return total runs before a single order has loaded, and you get 0 every time.",
        ],
        "fix_note": "use for...of (or Promise.all to run them in parallel):",
        "diff": [(" ", "  let total = 0;"),
                 ("-", "  ids.forEach(async (id) => {"),
                 ("+", "  for (const id of ids) {"),
                 (" ", "    const order = await fetchOrder(id);"),
                 (" ", "    total += order.amount;"),
                 ("-", "  });"),
                 ("+", "  }"),
                 (" ", "  return total;")],
    },
    {
        "slug": "sql-injection",
        "lang": "python",
        "filename": "users.py",
        "cover": [("this user lookup", "bold"), ("came straight from ai.", "bold"),
                  None, ("anyone can dump your users table.", "regular")],
        "question": "what's the problem?",
        "code": '''def get_user(name):
    sql = ("SELECT * FROM users "
           f"WHERE name = '{name}'")
    return db.execute(sql).fetchall()''',
        "answer": "sql injection",
        "explain": [
            "the name goes straight into the query text. type this as the name:",
            "$ ' OR '1'='1",
            "the query becomes WHERE name = '' OR '1'='1', which is true for every row. you just returned every user.",
        ],
        "fix_note": "pass values as parameters, never in the string:",
        "diff": [(" ", '    sql = ("SELECT * FROM users "'),
                 ("-", "           f\"WHERE name = '{name}'\")"),
                 ("+", '           "WHERE name = ?")'),
                 ("-", "    return db.execute(sql).fetchall()"),
                 ("+", "    return db.execute(sql, (name,)).fetchall()")],
    },
    {
        "slug": "api-key-frontend",
        "lang": "javascript",
        "filename": "frontend/src/chat.js",
        "cover": [("ai built this chat feature", "bold"), ("in 30 seconds.", "bold"),
                  None, ("it could cost you thousands.", "regular")],
        "question": "what's wrong with this?",
        "code": '''const API_KEY = "sk-live-8f3a91c2...";

export async function askAI(msg) {
  const res = await fetch(AI_URL, {
    method: "POST",
    headers: { "x-api-key": API_KEY },
    body: JSON.stringify({ msg }),
  });
  return res.json();
}''',
        "answer": "your secret key ships to every browser",
        "explain": [
            "this is frontend code. all of it gets bundled and downloaded by every visitor.",
            "anyone can open devtools, copy the key and run up your bill. moving it to a .env file doesn't help if the frontend still reads it.",
        ],
        "fix_note": "call your own backend. the key stays on the server:",
        "diff": [("-", 'const API_KEY = "sk-live-8f3a91c2...";'),
                 ("-", "  const res = await fetch(AI_URL, {"),
                 ("+", '  const res = await fetch("/api/chat", {'),
                 (" ", '    method: "POST",'),
                 ("-", '    headers: { "x-api-key": API_KEY },'),
                 ("+", "    // your server adds the key"),
                 (" ", "    body: JSON.stringify({ msg }),")],
    },
]
