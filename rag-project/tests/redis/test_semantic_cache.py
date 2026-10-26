import config


def test_stored_answer_is_found_again(isolated_cache):
    sc = isolated_cache
    sc.store_cache_entry(
        "Where is the spare tyre in a sedan?", "Under the boot floor.", "groq"
    )
    hit = sc.find_cached_answer("Where is the spare tyre in a sedan?")
    assert hit is not None
    assert hit["answer"] == "Under the boot floor."
    assert hit["provider"] == "groq"
    assert hit["similarity"] >= config.CACHE_SIMILARITY_THRESHOLD


def test_unrelated_query_is_a_miss(isolated_cache):
    sc = isolated_cache
    sc.store_cache_entry(
        "Where is the spare tyre in a sedan?", "Under the boot floor.", "groq"
    )
    assert sc.find_cached_answer("zebra quantum lemonade symphony") is None


def test_empty_cache_is_a_miss(isolated_cache):
    assert isolated_cache.find_cached_answer("anything at all") is None


def test_same_words_for_a_different_vehicle_type_are_blocked_by_the_entity_guard(
    isolated_cache,
):
    sc = isolated_cache
    sc.store_cache_entry(
        "Where is the spare tyre in a sedan?", "Under the boot floor.", "groq"
    )
    assert sc.find_cached_answer("Where is the spare tyre in an suv?") is None


def test_entries_expire(isolated_cache, client):
    sc = isolated_cache
    sc.store_cache_entry("tyre question", "answer", "groq")
    keys = list(client.scan_iter(match=f"{sc.CACHE_KEY_PREFIX}*"))
    assert len(keys) == 1
    assert 0 < client.ttl(keys[0]) <= config.CACHE_TTL_SECONDS


def test_clear_cache_removes_only_this_prefix(isolated_cache, client):
    sc = isolated_cache
    sc.store_cache_entry("one", "a", "groq")
    sc.store_cache_entry("two", "b", "groq")
    client.set("unrelated:key", "keep")
    try:
        assert sc.clear_cache() == 2
        assert sc.find_cached_answer("one") is None
        assert client.get("unrelated:key") == "keep"
    finally:
        client.delete("unrelated:key")


def test_create_cache_index_is_idempotent(isolated_cache):
    isolated_cache.create_cache_index()
    isolated_cache.create_cache_index()


def test_a_prompt_change_invalidates_existing_entries(isolated_cache, monkeypatch):
    sc = isolated_cache
    sc.store_cache_entry("Where is the jack?", "In the boot.", "groq")
    assert sc.find_cached_answer("Where is the jack?", "groq") is not None

    monkeypatch.setattr(sc, "PROMPT_VERSION", "edited-prompts")
    assert sc.find_cached_answer("Where is the jack?", "groq") is None


def test_entries_are_scoped_to_the_answering_model(isolated_cache):
    sc = isolated_cache
    sc.store_cache_entry("Where is the jack?", "In the boot.", "groq")
    assert sc.find_cached_answer("Where is the jack?", "gemini") is None


def test_a_hit_returns_the_grounding_stored_with_the_answer(isolated_cache, client):
    sc = isolated_cache
    grounding = {
        "sources": ["tyre.pdf"],
        "chunks_used": 5,
        "sufficiency": {"sufficient": True, "reason": "ok", "tier": "llm_judge"},
        "citation_check": {
            "grounded": True,
            "unsupported_claims": [],
            "reason": "ok",
            "tier": "llm_judge",
        },
        "confidence": "high",
    }
    sc.store_cache_entry(
        "Where is the jack?", "In the boot [SOURCE 1].", "groq", None, grounding
    )
    assert sc.find_cached_answer("Where is the jack?", "groq")["grounding"] == grounding

    # An entry written before grounding was stored still hits, with no grounding.
    for key in client.scan_iter(match=f"{sc.CACHE_KEY_PREFIX}*"):
        client.hdel(key, "grounding")
    hit = sc.find_cached_answer("Where is the jack?", "groq")
    assert hit["answer"] == "In the boot [SOURCE 1]."
    assert hit["grounding"] == {}
