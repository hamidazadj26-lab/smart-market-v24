from datetime import datetime, timezone
from app.services.intelligence_map import feature, feature_collection, in_bbox, valid_coordinates


def test_coordinates_are_strict_and_never_coerced_from_booleans():
    assert valid_coordinates(35.7, 51.4)
    assert valid_coordinates(90, 180)
    assert not valid_coordinates(91, 0)
    assert not valid_coordinates(0, -181)
    assert not valid_coordinates(float('nan'), 0)
    assert not valid_coordinates(float('inf'), 0)
    assert not valid_coordinates(True, 1)
    assert not valid_coordinates('Tehran', '51.4')


def test_feature_preserves_provenance_and_coordinate_order():
    observed = datetime(2026, 10, 12, tzinfo=timezone.utc)
    item = feature('customer', 7, 'Buyer', 36.3, 59.6, 'Iran', 'Mashhad',
                   'Potential', 0.8, 'https://example.org/profile', 'Profile', observed)
    assert item['geometry']['coordinates'] == [59.6, 36.3]
    assert item['properties']['source_url'] == 'https://example.org/profile'
    assert item['properties']['location_basis'] == 'stored_coordinates'
    assert item['properties']['observed_at'] == observed.isoformat()


def test_invalid_location_is_not_exported_and_confidence_is_bounded():
    assert feature('customer', 1, 'Bad', 100, 200) is None
    item = feature('customer', 2, 'Unknown confidence', 0, 0, confidence=5)
    assert item['properties']['confidence'] is None


def test_bbox_filters_points_and_handles_antimeridian():
    tehran = feature('manufacturer', 1, 'Tehran', 35.7, 51.4)
    fiji = feature('customer', 2, 'Fiji', -17.7, 178.1)
    assert in_bbox(tehran, (40, 25, 60, 40))
    assert not in_bbox(tehran, (100, 25, 120, 40))
    assert in_bbox(fiji, (170, -30, -170, 0))
    collection = feature_collection([tehran, fiji], (40, 25, 60, 40), 10)
    assert collection['meta']['returned'] == 1
    assert collection['meta']['matched'] == 1


def test_collection_caps_results_and_reports_truncation():
    items = [feature('customer', i, str(i), 0, i) for i in range(1, 4)]
    collection = feature_collection(items, limit=2)
    assert collection['meta']['returned'] == 2
    assert collection['meta']['matched'] == 3
    assert collection['meta']['truncated'] is True
