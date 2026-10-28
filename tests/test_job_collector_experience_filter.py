
from unittest.mock import Mock, patch

from src.ingestion.job_collector import JobCollector


def make_collector():
    evaluator = Mock()
    repository = Mock()

    evaluator.experience_matcher.get_match_result.side_effect = (
        lambda experience: {
            "job_min_experience": 12 if experience == "12-20 Yrs" else 0,
            "job_max_experience": 20 if experience == "12-20 Yrs" else 2,
            "candidate_min_experience": 0,
            "candidate_max_experience": 2,
            "match": experience != "12-20 Yrs" and bool(experience),
        }
    )

    collector = JobCollector(evaluator, repository)
    return collector, evaluator, repository


def test_out_of_range_job_is_skipped_before_storage():
    collector, evaluator, repository = make_collector()

    with patch("src.ingestion.job_collector.JDExtractor") as extractor_class:
        extractor_class.return_value.extract_all.return_value = {
            "title": "Data Analyst",
            "experience": "12-20 Yrs",
            "skills": ["SQL"],
        }

        result = collector.process_job(
            job_description="Test description",
            job_url="https://example.com/job/1",
        )

    assert result["skipped"] is True
    assert result["inserted"] is False
    assert result["updated"] is False
    assert result["evaluation"] is None
    evaluator.evaluate.assert_not_called()
    repository.job_exists.assert_not_called()
    repository.add_job.assert_not_called()
    repository.update_job.assert_not_called()


def test_matching_experience_continues_to_evaluation():
    collector, evaluator, repository = make_collector()

    evaluator.evaluate.return_value = {
        "final_score": 75,
        "score_category": "Good Match",
    }
    repository.job_exists.return_value = False
    repository.add_job.return_value = True

    with patch("src.ingestion.job_collector.JDExtractor") as extractor_class:
        extractor_class.return_value.extract_all.return_value = {
            "title": "Junior Data Analyst",
            "experience": "0-2 years",
            "skills": ["SQL"],
        }

        result = collector.process_job(
            job_description="Test description",
            job_url="https://example.com/job/2",
        )

    assert result["skipped"] is False
    assert result["inserted"] is True
    evaluator.evaluate.assert_called_once()
    repository.add_job.assert_called_once()
