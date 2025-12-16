"""Shared processors - only query_execution remains as scheme-agnostic"""
from .query_execution import execute_query

__all__ = ['execute_query']
