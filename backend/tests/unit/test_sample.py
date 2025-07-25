"""
간단한 샘플 테스트
"""
import pytest
from unittest.mock import Mock, patch


class TestSample:
    """샘플 테스트 클래스"""
    
    def test_basic_addition(self):
        """기본 덧셈 테스트"""
        assert 1 + 1 == 2
        
    def test_string_concatenation(self):
        """문자열 연결 테스트"""
        result = "Hello" + " " + "World"
        assert result == "Hello World"
        
    def test_list_operations(self):
        """리스트 연산 테스트"""
        my_list = [1, 2, 3]
        my_list.append(4)
        assert len(my_list) == 4
        assert my_list[-1] == 4
        
    def test_dictionary_operations(self):
        """딕셔너리 연산 테스트"""
        my_dict = {"key1": "value1"}
        my_dict["key2"] = "value2"
        assert "key2" in my_dict
        assert my_dict["key2"] == "value2"
        
    @pytest.mark.parametrize("input,expected", [
        (0, 0),
        (1, 1),
        (2, 4),
        (3, 9),
        (4, 16)
    ])
    def test_square_function(self, input, expected):
        """제곱 함수 테스트"""
        def square(x):
            return x * x
            
        assert square(input) == expected
        
    def test_mock_example(self):
        """Mock 사용 예제"""
        mock_obj = Mock()
        mock_obj.method.return_value = "mocked value"
        
        result = mock_obj.method()
        assert result == "mocked value"
        mock_obj.method.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])