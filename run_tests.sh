#!/bin/bash
# Test Runner Script for Voice Kiosk

echo "=========================================="
echo "  Voice Kiosk Test Suite"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "config.py" ]; then
    echo "Error: Must be run from voice-kiosk directory"
    exit 1
fi

# Parse command line arguments
TEST_TYPE="${1:-all}"

case "$TEST_TYPE" in
    unit)
        echo "Running non-interactive unit tests..."
        echo ""
        python3 test_unit.py
        exit $?
        ;;

    interactive)
        echo "Running interactive hardware tests..."
        echo ""
        python3 test_interactive.py
        exit $?
        ;;

    all)
        echo "Running all tests..."
        echo ""

        # Run unit tests first
        echo "=========================================="
        echo "  Part 1: Unit Tests (Non-Interactive)"
        echo "=========================================="
        echo ""
        python3 test_unit.py
        UNIT_RESULT=$?

        echo ""
        echo "=========================================="
        echo "  Part 2: Hardware Tests (Interactive)"
        echo "=========================================="
        echo ""
        echo "These tests require user interaction."
        read -p "Continue with interactive tests? (y/n) " -n 1 -r
        echo ""

        if [[ $REPLY =~ ^[Yy]$ ]]; then
            python3 test_interactive.py
            INTERACTIVE_RESULT=$?
        else
            echo "Skipped interactive tests"
            INTERACTIVE_RESULT=0
        fi

        # Print summary
        echo ""
        echo "=========================================="
        echo "  Test Results Summary"
        echo "=========================================="
        if [ $UNIT_RESULT -eq 0 ]; then
            echo "✅ Unit tests: PASSED"
        else
            echo "❌ Unit tests: FAILED"
        fi

        if [ $INTERACTIVE_RESULT -eq 0 ]; then
            echo "✅ Interactive tests: PASSED"
        else
            echo "❌ Interactive tests: FAILED"
        fi

        # Return non-zero if any failed
        if [ $UNIT_RESULT -ne 0 ] || [ $INTERACTIVE_RESULT -ne 0 ]; then
            exit 1
        fi
        exit 0
        ;;

    *)
        echo "Usage: $0 [unit|interactive|all]"
        echo ""
        echo "  unit        - Run non-interactive unit tests only"
        echo "  interactive - Run interactive hardware tests only"
        echo "  all         - Run all tests (default)"
        echo ""
        exit 1
        ;;
esac
