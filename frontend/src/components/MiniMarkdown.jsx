// Tiny, safe renderer for assistant answers: paragraphs, bullet and numbered
// lists, and **bold**. Text is rendered as React text, never as raw HTML.

const inline = (text, keyBase) =>
  text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**') && part.length > 4
      ? <strong key={`${keyBase}-${i}`}>{part.slice(2, -2)}</strong>
      : part
  );

export const MiniMarkdown = ({ text }) => {
  const blocks = [];
  let list = null;

  const flush = () => {
    if (list) blocks.push(list);
    list = null;
  };

  text.split('\n').forEach((raw) => {
    const line = raw.trimEnd();
    const bullet = line.match(/^\s*[-*•]\s+(.*)$/);
    const numbered = line.match(/^\s*\d+[.)]\s+(.*)$/);
    if (bullet || numbered) {
      const type = bullet ? 'ul' : 'ol';
      if (!list || list.type !== type) {
        flush();
        list = { type, items: [] };
      }
      list.items.push((bullet || numbered)[1]);
    } else if (line.trim()) {
      flush();
      blocks.push({ type: 'p', text: line.replace(/^#+\s*/, '') });
    } else {
      flush();
    }
  });
  flush();

  return (
    <div className="space-y-2">
      {blocks.map((b, i) => {
        if (b.type === 'p') return <p key={i}>{inline(b.text, i)}</p>;
        const List = b.type;
        return (
          <List key={i} className={`${b.type === 'ul' ? 'list-disc' : 'list-decimal'} pl-5 space-y-1`}>
            {b.items.map((it, j) => <li key={j}>{inline(it, `${i}-${j}`)}</li>)}
          </List>
        );
      })}
    </div>
  );
};
