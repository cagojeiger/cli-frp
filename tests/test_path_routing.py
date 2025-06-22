"""Tests for path routing system."""

import pytest
from frp_wrapper.path_routing import (
    PathPattern,
    PathConflictDetector,
    PathValidator,
    PathConflict,
    PathConflictType
)


class TestPathPattern:
    """Test PathPattern class"""
    
    def test_exact_pattern_matching(self):
        """Test exact pattern matching"""
        pattern = PathPattern("/api/users")
        
        assert pattern.matches("/api/users")
        assert not pattern.matches("/api/user")
        assert not pattern.matches("/api/users/1")
        assert not pattern.is_wildcard
    
    def test_single_wildcard_pattern(self):
        """Test single wildcard pattern matching"""
        pattern = PathPattern("/api/*")
        
        assert pattern.matches("/api/users")
        assert pattern.matches("/api/posts")
        assert not pattern.matches("/api/users/1")  # * doesn't match /
        assert not pattern.matches("/api")
        assert pattern.is_wildcard
        assert not pattern.is_recursive
    
    def test_recursive_wildcard_pattern(self):
        """Test recursive wildcard pattern matching"""
        pattern = PathPattern("/api/**")
        
        assert pattern.matches("/api/users")
        assert pattern.matches("/api/users/1")
        assert pattern.matches("/api/users/1/posts")
        assert not pattern.matches("/api")
        assert pattern.is_wildcard
        assert pattern.is_recursive
    
    def test_pattern_conflicts(self):
        """Test pattern conflict detection"""
        pattern1 = PathPattern("/api/users")
        pattern2 = PathPattern("/api/users")
        assert pattern1.conflicts_with(pattern2)
        
        pattern3 = PathPattern("/api/*")
        pattern4 = PathPattern("/api/users")
        assert pattern3.conflicts_with(pattern4)
        assert pattern4.conflicts_with(pattern3)
        
        pattern5 = PathPattern("/api/users")
        pattern6 = PathPattern("/app/users")
        assert not pattern5.conflicts_with(pattern6)
    
    def test_pattern_string_representation(self):
        """Test pattern string representation"""
        pattern = PathPattern("/api/*")
        assert str(pattern) == "/api/*"
        assert repr(pattern) == "PathPattern('/api/*')"


class TestPathConflictDetector:
    """Test PathConflictDetector class"""
    
    def test_register_and_unregister_paths(self):
        """Test path registration and unregistration"""
        detector = PathConflictDetector()
        
        detector.register_path("/api/users", "tunnel1")
        detector.register_path("/app/*", "tunnel2")
        
        active_paths = detector.get_active_paths()
        assert active_paths == {"/api/users": "tunnel1", "/app/*": "tunnel2"}
        
        detector.unregister_path("/api/users")
        active_paths = detector.get_active_paths()
        assert active_paths == {"/app/*": "tunnel2"}
    
    def test_check_conflict_simple(self):
        """Test simple conflict checking"""
        detector = PathConflictDetector()
        
        result = detector.check_conflict("/api/users", [])
        assert result is None
        
        result = detector.check_conflict("/api/users", ["/api/users"])
        assert result is not None
        assert "conflicts with" in result
        
        result = detector.check_conflict("/api/users", ["/app/users"])
        assert result is None
    
    def test_detect_conflicts_comprehensive(self):
        """Test comprehensive conflict detection"""
        detector = PathConflictDetector()
        
        detector.register_path("/api/users", "tunnel1")
        detector.register_path("/app/*", "tunnel2")
        detector.register_path("/static/**", "tunnel3")
        
        conflicts = detector.detect_conflicts("/api/users", "tunnel4")
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == PathConflictType.EXACT_MATCH
        assert conflicts[0].existing_tunnel_id == "tunnel1"
        
        conflicts = detector.detect_conflicts("/app/dashboard", "tunnel5")
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == PathConflictType.WILDCARD_OVERLAP
        assert conflicts[0].existing_tunnel_id == "tunnel2"
        
        conflicts = detector.detect_conflicts("/blog/posts", "tunnel6")
        assert len(conflicts) == 0
    
    def test_clear_paths(self):
        """Test clearing all paths"""
        detector = PathConflictDetector()
        
        detector.register_path("/api/users", "tunnel1")
        detector.register_path("/app/*", "tunnel2")
        
        assert len(detector.get_active_paths()) == 2
        
        detector.clear()
        assert len(detector.get_active_paths()) == 0


class TestPathValidator:
    """Test PathValidator class"""
    
    def test_normalize_path(self):
        """Test path normalization"""
        assert PathValidator.normalize_path("/api/users/") == "api/users"
        assert PathValidator.normalize_path("api/users") == "api/users"
        
        assert PathValidator.normalize_path("") == ""
        assert PathValidator.normalize_path("/") == ""
        
        assert PathValidator.normalize_path("api//users///posts") == "api/users/posts"
    
    def test_validate_path(self):
        """Test path validation"""
        assert PathValidator.validate_path("api/users")
        assert PathValidator.validate_path("api/*")
        assert PathValidator.validate_path("api/**")
        assert PathValidator.validate_path("api/users/*/posts")
        
        assert not PathValidator.validate_path("")  # Empty
        assert not PathValidator.validate_path("api<users")  # Invalid char
        assert not PathValidator.validate_path("api>users")  # Invalid char
        assert not PathValidator.validate_path('api"users')  # Invalid char
        assert not PathValidator.validate_path("api|users")  # Invalid char
        assert not PathValidator.validate_path("api?users")  # Invalid char
        assert not PathValidator.validate_path("api\\users")  # Invalid char
        assert not PathValidator.validate_path("api/***")  # Triple asterisk
        assert not PathValidator.validate_path("api/**/*")  # Invalid wildcard combo
        assert not PathValidator.validate_path("api/*/**")  # Invalid wildcard combo
    
    def test_extract_base_path(self):
        """Test base path extraction"""
        assert PathValidator.extract_base_path("api/users") == "api/users"
        
        assert PathValidator.extract_base_path("api/*") == "api"
        assert PathValidator.extract_base_path("api/users/*") == "api/users"
        
        assert PathValidator.extract_base_path("api/**") == "api"
        assert PathValidator.extract_base_path("api/users/**") == "api/users"
        
        assert PathValidator.extract_base_path("*") == ""
        assert PathValidator.extract_base_path("**") == ""


class TestPathConflict:
    """Test PathConflict dataclass"""
    
    def test_path_conflict_creation(self):
        """Test PathConflict creation"""
        conflict = PathConflict(
            conflict_type=PathConflictType.EXACT_MATCH,
            existing_path="/api/users",
            new_path="/api/users",
            existing_tunnel_id="tunnel1",
            message="Test conflict"
        )
        
        assert conflict.conflict_type == PathConflictType.EXACT_MATCH
        assert conflict.existing_path == "/api/users"
        assert conflict.new_path == "/api/users"
        assert conflict.existing_tunnel_id == "tunnel1"
        assert conflict.message == "Test conflict"


class TestPathRoutingIntegration:
    """Integration tests for path routing system"""
    
    def test_full_workflow(self):
        """Test complete path routing workflow"""
        detector = PathConflictDetector()
        
        paths_to_register = [
            ("/api/users", "tunnel1"),
            ("/app/*", "tunnel2"),
            ("/static/**", "tunnel3")
        ]
        
        for path, tunnel_id in paths_to_register:
            normalized = PathValidator.normalize_path(path)
            assert PathValidator.validate_path(normalized)
            
            conflicts = detector.detect_conflicts(normalized, tunnel_id)
            assert len(conflicts) == 0  # No conflicts initially
            
            detector.register_path(normalized, tunnel_id)
        
        conflicting_path = "/api/users"
        normalized_conflicting = PathValidator.normalize_path(conflicting_path)
        conflicts = detector.detect_conflicts(normalized_conflicting, "tunnel4")
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == PathConflictType.EXACT_MATCH
        
        new_path = "/blog/posts"
        conflicts = detector.detect_conflicts(new_path, "tunnel5")
        assert len(conflicts) == 0
        
        detector.register_path(new_path, "tunnel5")
        assert len(detector.get_active_paths()) == 4
    
    def test_tunnel_manager_integration(self):
        """Test PathConflictDetector integration with TunnelManager"""
        from frp_wrapper.tunnel_manager import TunnelManager, TunnelManagerError
        from frp_wrapper.tunnel import TunnelConfig
        
        config = TunnelConfig(
            server_host="test.example.com",
            auth_token="test_token",
            default_domain="example.com"
        )
        
        manager = TunnelManager(config, frp_binary_path="/usr/bin/frpc")
        
        tunnel1 = manager.create_http_tunnel(
            tunnel_id="test1",
            local_port=8080,
            path="api/users"
        )
        
        assert tunnel1.path == "api/users"
        active_paths = manager._path_detector.get_active_paths()
        assert "api/users" in active_paths
        assert active_paths["api/users"] == "test1"
        
        with pytest.raises(TunnelManagerError) as exc_info:
            manager.create_http_tunnel(
                tunnel_id="test2",
                local_port=8081,
                path="/api/users"  # Should conflict
            )
        assert "Path conflicts detected" in str(exc_info.value)
        
        with pytest.raises(TunnelManagerError) as exc_info:
            manager.create_http_tunnel(
                tunnel_id="test3",
                local_port=8082,
                path="api/*"  # Should conflict with api/users
            )
        assert "Path conflicts detected" in str(exc_info.value)
        
        manager.remove_tunnel("test1")
        active_paths = manager._path_detector.get_active_paths()
        assert "api/users" not in active_paths
        
        tunnel2 = manager.create_http_tunnel(
            tunnel_id="test2",
            local_port=8081,
            path="/api/users"
        )
        assert tunnel2.path == "api/users"
    
    def test_path_validation_integration(self):
        """Test path validation integration with conflict detection"""
        from frp_wrapper.tunnel_manager import TunnelManager, TunnelManagerError
        from frp_wrapper.tunnel import TunnelConfig
        
        config = TunnelConfig(
            server_host="test.example.com",
            auth_token="test_token"
        )
        
        manager = TunnelManager(config, frp_binary_path="/usr/bin/frpc")
        
        with pytest.raises(TunnelManagerError) as exc_info:
            manager.create_http_tunnel(
                tunnel_id="invalid1",
                local_port=8080,
                path="api<invalid"  # Invalid character
            )
        assert "Invalid path format" in str(exc_info.value)
        
        with pytest.raises(TunnelManagerError) as exc_info:
            manager.create_http_tunnel(
                tunnel_id="invalid2",
                local_port=8080,
                path=""  # Empty path
            )
        assert "Invalid path format" in str(exc_info.value)
        
        tunnel = manager.create_http_tunnel(
            tunnel_id="normalized",
            local_port=8080,
            path="/api//users///posts/"  # Should be normalized
        )
        assert tunnel.path == "api/users/posts"
    
    def test_multiple_conflict_types(self):
        """Test detection of different conflict types"""
        detector = PathConflictDetector()
        
        detector.register_path("api/users", "tunnel1")
        detector.register_path("app/*", "tunnel2")
        detector.register_path("static/**", "tunnel3")
        
        conflicts = detector.detect_conflicts("api/users", "tunnel4")
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == PathConflictType.EXACT_MATCH
        
        conflicts = detector.detect_conflicts("app/dashboard", "tunnel5")
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == PathConflictType.WILDCARD_OVERLAP
        
        conflicts = detector.detect_conflicts("static/css/main.css", "tunnel6")
        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == PathConflictType.WILDCARD_OVERLAP
        
        conflicts = detector.detect_conflicts("blog/posts", "tunnel7")
        assert len(conflicts) == 0
