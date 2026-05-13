/** RAG recurrence: "new" (no vector matches) vs "known" (has similar_insights). */
function RecurrenceTag({ recurrence }) {
  const known = recurrence === "known";
  const label = known ? "known" : "new";
  const hint = known
    ? "This theme matched similar problems from past analyses."
    : "No close matches in past analyses (or RAG unavailable).";

  return (
    <span
      className={`recurrence-pill recurrence-pill--${known ? "known" : "new"}`}
      title={hint}
    >
      {label}
    </span>
  );
}

export default RecurrenceTag;
