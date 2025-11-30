import json

def loadAndClean(ref):
    with open(ref, 'r') as r:
        data = json.load(r)

    for list in data:
        list.pop("Author", None)
    newData= []
    test = []

    for comment in data:
        if ((comment['Likes']) != ''):
            newData.append(comment)
    
    for comment in newData:
        if (int(comment['Likes']) >= 10):
            test.append(comment)

    keywords = [
        "add", "feature", "wish", "need", "could", "missing", "support",
        "issue", "bug", "problem", "crash", "lag", "slow", "broken", "fix",
        "hard", "confusing", "complicated", "clear", "should be easier",
        "unlike", "other tool", "competitor", "better",
        "automatic", "AI", "automate", "future", "huge if"
    ]

    filtered = []

    for comment in test:
        for word in keywords:
            if word in comment["Text"]:
                filtered.append(comment)
    print(filtered)
    print(len(filtered))

#loadAndClean('Datasets/Practice.json')
loadAndClean('Datasets/2025.json')