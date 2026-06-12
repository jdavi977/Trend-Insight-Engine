"""Eval surface (PRD §7.9 / slice 3 §4).

A developer tool that *drives* the real v2 pipeline like a test harness and
scores its output against a hand-labelled seed set. Deliberately kept out of the
request-serving `api/ → services/` path: it imports the same services production
uses (no parallel reimplementation) but bypasses HTTP, rate limits, and the
budget cap. It is never imported by the running app.
"""
