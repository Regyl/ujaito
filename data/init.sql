CREATE TABLE IF NOT EXISTS questions (
    featured_question_id BIGINT PRIMARY KEY,
    question TEXT NOT NULL,
    source TEXT,
    due_date TIMESTAMPTZ,
    public_link TEXT,
    source_url TEXT,
    is_haro_query BOOLEAN,
    categories JSONB NOT NULL DEFAULT '[]'::jsonb,
    can_solve BOOLEAN NOT NULL,
    fit_reason TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    source TEXT NOT NULL,
    board TEXT NOT NULL,
    job_id BIGINT NOT NULL,
    title TEXT NOT NULL,
    absolute_url TEXT NOT NULL,
    location TEXT NOT NULL,
    content TEXT NOT NULL,
    payload JSONB NOT NULL,
    PRIMARY KEY (source, board, job_id)
);
