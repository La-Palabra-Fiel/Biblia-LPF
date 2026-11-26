CREATE TABLE IF NOT EXISTS review_links (
  book TEXT NOT NULL,
  reviewer TEXT NOT NULL,
  reviewer_key TEXT NOT NULL,
  token_hash TEXT NOT NULL PRIMARY KEY CHECK (length(token_hash) = 64),
  created_on TEXT NOT NULL,
  revoked_on TEXT,
  UNIQUE (book, reviewer_key)
);

CREATE INDEX IF NOT EXISTS review_links_book
  ON review_links (book, revoked_on);

CREATE TABLE IF NOT EXISTS signatures (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  book TEXT NOT NULL,
  reviewer TEXT NOT NULL,
  reviewer_key TEXT NOT NULL,
  signed_name TEXT NOT NULL,
  signed_on TEXT NOT NULL,
  translation_sha256 TEXT NOT NULL CHECK (length(translation_sha256) = 64),
  statement TEXT NOT NULL,
  UNIQUE (book, reviewer_key, translation_sha256)
);

CREATE INDEX IF NOT EXISTS signatures_current_book
  ON signatures (book, translation_sha256, signed_on);

