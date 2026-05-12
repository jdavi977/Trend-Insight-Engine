# Usage Guide

## Overview

Trend Insight Engine has two modes:

- **Manual analysis** — paste any YouTube video URL or App Store app URL and get instant insights from its comments/reviews
- **Weekly feed** — pre-generated insights for popular videos and apps, refreshed by the automated pipeline

---

## Manual Analysis

### YouTube

1. Go to the **YouTube** tab
2. Paste a video URL into the input field:
   - `https://www.youtube.com/watch?v=VIDEO_ID`
   - `https://youtu.be/VIDEO_ID`
3. Press **Analyze** (or hit Enter)
4. Wait 10–30 seconds while comments are fetched and analyzed

### App Store

1. Go to the **App Store** tab
2. Paste an App Store URL:
   - `https://apps.apple.com/us/app/app-name/id123456789`
3. Press **Analyze**

> Only US App Store URLs are supported. The `id` at the end of the URL is what matters — the app name slug can differ.

---

## Reading Results

Each analysis surfaces a list of **problems** extracted from the comments or reviews.

### Problem card fields

| Field | What it means |
|-------|---------------|
| **Problem** | One-sentence description of the recurring issue or request |
| **Type** | Category of the problem (see below) |
| **Severity** | How painful or impactful the problem is (1–5) |
| **Frequency** | How often the theme appears in the dataset (1–5) |
| **Total likes** (YouTube) | Sum of likes across all comments grouped under this problem |
| **Average rating** (App Store) | Mean star rating of the reviews grouped under this problem |

### Problem types

| Type | Meaning |
|------|---------|
| `feature_request` | Users want a capability that doesn't exist yet |
| `complaint` | Users are unhappy with existing behavior |
| `usability` | Confusing UX, hard onboarding, or navigation friction |
| `performance` | Crashes, lag, slow load, freezing, battery drain |
| `pricing` | Subscription issues, paywalls, perceived poor value |
| `other` | Doesn't fit the above — still worth reviewing |

### Severity scale (1–5)

| Score | Meaning |
|-------|---------|
| 1 | Minor annoyance — most users work around it |
| 2 | Noticeable friction but doesn't block usage |
| 3 | Affects normal use or causes real confusion |
| 4 | Causes churn risk or significant frustration |
| 5 | App-breaking, data loss, safety risk, or deceptive billing |

### Frequency scale (1–5)

| Score | Meaning |
|-------|---------|
| 1 | Rare — mentioned by very few |
| 2 | Occasional — a minority of users mention it |
| 3 | Consistent — appears across the dataset |
| 4 | Common — a clear recurring theme |
| 5 | Dominant — the most prevalent issue in the dataset |

> **Tip:** Prioritize problems that score high on both. High severity + high frequency = the issues most likely to drive churn or block adoption.

---

## Home and Insights Pages

The **Home** page shows the weekly top YouTube videos with their extracted insights. The **Insights** page shows all videos and apps from the latest pipeline run, with a category filter.

These pages are populated by the automated weekly pipeline — see [DATA_SOURCES.md](DATA_SOURCES.md) for what categories are covered and how often data refreshes.

---

## Retrieved Context (RAG)

After an analysis, you may see a **Retrieved Context** section below the results. This shows similar insights retrieved from past analyses stored in the database. Use it to spot recurring patterns across videos or apps you've analyzed previously.
