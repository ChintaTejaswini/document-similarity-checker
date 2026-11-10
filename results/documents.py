"""
Document intake (no maths here).

Turns uploaded .txt files and manually typed lines into one list of documents,
each with a unique label, and reports every file that had to be skipped or fixed.

    collect_documents(files, manual_text) -> (labels, texts, notes)

    files        list of (filename, raw_bytes)
    manual_text  text typed by the user, one document per line
    notes        list of (level, message) with level "warning" or "info"
"""
import os


# ----------------------------------------------------------------------------
# Decoding
# ----------------------------------------------------------------------------
def decode_bytes(data):
    """Decode raw bytes to text. Returns (text, encoding_used) or (None, reason).

    Tries UTF-8 (with or without BOM), UTF-16 (only when a BOM says so), then the
    common Windows code page cp1252.  Files that look binary (NUL bytes) are refused.
    """
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        try:
            return data.decode("utf-16"), "utf-16"
        except UnicodeError:
            return None, "it is not valid UTF-16 text"
    if b"\x00" in data:
        return None, "it looks like a binary file, not plain text"
    try:
        return data.decode("utf-8-sig"), "utf-8"
    except UnicodeDecodeError:
        pass
    try:
        return data.decode("cp1252"), "cp1252"
    except UnicodeDecodeError:
        # cp1252 leaves a few byte values undefined; latin-1 maps every byte
        return data.decode("latin-1"), "latin-1"


# ----------------------------------------------------------------------------
# Unique labels
# ----------------------------------------------------------------------------
def unique_label(name, taken):
    """name, or 'name (2)', 'name (3)' ... (before the extension) if already taken."""
    if name not in taken:
        return name
    stem, ext = os.path.splitext(name)
    k = 2
    while f"{stem} ({k}){ext}" in taken:
        k += 1
    return f"{stem} ({k}){ext}"


# ----------------------------------------------------------------------------
# Main entry point
# ----------------------------------------------------------------------------
def collect_documents(files, manual_text="", manual_prefix="D", usable=None):
    """Uploaded files first (in upload order), then manual lines.

    Every file is ONE document labelled with its filename; every non-empty manual
    line is one document labelled D1, D2 ... (counted among the manual lines only).
    Empty, binary or unreadable files are skipped and reported in `notes`.
    `usable(text) -> bool` (optional) lets the caller reject documents that have no words
    left after cleaning; rejected files are reported, rejected manual lines are ignored.
    """
    labels, texts, notes = [], [], []
    taken = set()
    skipped_empty, skipped_bad, skipped_words, renamed, recoded = [], [], [], [], []

    for name, data in files:
        name = os.path.basename(str(name).replace("\\", "/")) or "unnamed.txt"
        if not data or not data.strip():
            skipped_empty.append(name)
            continue
        text, how = decode_bytes(data)
        if text is None:
            skipped_bad.append(f"{name} ({how})")
            continue
        text = text.replace("\x00", "").strip()
        if not text:
            skipped_empty.append(name)
            continue
        if usable is not None and not usable(text):
            skipped_words.append(name)
            continue
        label = unique_label(name, taken)
        if label != name:
            renamed.append(f"{name} → {label}")
        if how not in ("utf-8", "utf-16"):
            recoded.append(f"{name} ({how})")
        taken.add(label)
        labels.append(label)
        texts.append(text)

    k = 0
    for line in (manual_text or "").splitlines():
        line = line.strip()
        if not line or (usable is not None and not usable(line)):
            continue
        k += 1
        label = unique_label(f"{manual_prefix}{k}", taken)
        taken.add(label)
        labels.append(label)
        texts.append(line)

    if skipped_empty:
        notes.append(("warning", "Skipped empty file(s): " + ", ".join(skipped_empty) + "."))
    if skipped_words:
        notes.append(("warning", "Skipped file(s) with no usable words after cleaning (only punctuation, "
                                 "symbols or removed common words): " + ", ".join(skipped_words) + "."))
    if skipped_bad:
        notes.append(("warning", "Skipped file(s) that could not be read as text: " + "; ".join(skipped_bad) + "."))
    if renamed:
        notes.append(("info", "Duplicate filenames were numbered so every document keeps a unique label: "
                              + "; ".join(renamed) + "."))
    if recoded:
        notes.append(("info", "Not UTF-8, read with a fallback encoding: " + ", ".join(recoded) + "."))
    return labels, texts, notes
