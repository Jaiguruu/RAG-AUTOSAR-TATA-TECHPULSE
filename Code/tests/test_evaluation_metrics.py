from autosar_rag.evaluation_metrics import check_must_include


def test_exact_phrase_matches():
    result = check_must_include(
        "LdCom_Init initializes the module and returns E_OK on success.",
        "LdCom_Init | E_OK",
    )
    assert result["score"] == 1.0
    assert result["missing"] == []


def test_identifier_matches_with_spaces_instead_of_underscores():
    result = check_must_include("PduR LdComTransmit forwards the request.", "PduR_LdComTransmit")
    assert result["score"] == 1.0


def test_scattered_words_do_not_count_as_a_phrase():
    result = check_must_include(
        "The functionality differs. Later the API is described, and configuration is discussed elsewhere.",
        "functionality, API, and configuration",
    )
    assert result["score"] == 0.0
    assert result["missing"] == ["functionality, API, and configuration"]


def test_empty_criteria_is_not_scored_as_perfect():
    result = check_must_include("An answer", "  |  ")
    assert result["score"] is None
    assert result["scored"] is False
