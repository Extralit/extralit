#!/usr/bin/env python3
# Copyright 2024-present, Extralit Labs, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Simple test script to verify PDF_QUEUE is working correctly.
"""

import sys

# Add src to path
sys.path.insert(0, "src")


def test_pdf_queue():
    """Test that PDF_QUEUE can be imported and is configured correctly."""
    try:
        from extralit_server.jobs.queues import PDF_QUEUE

        print("✅ PDF_QUEUE imported successfully")
        print(f"✅ Queue name: {PDF_QUEUE.name}")
        print(f"✅ Queue connection: {type(PDF_QUEUE.connection).__name__}")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_all_queues():
    """Test that all queues are available."""
    try:
        from extralit_server.jobs.queues import DEFAULT_QUEUE, GPU_QUEUE, HIGH_QUEUE, PDF_QUEUE

        queues = {
            "DEFAULT_QUEUE": DEFAULT_QUEUE,
            "HIGH_QUEUE": HIGH_QUEUE,
            "GPU_QUEUE": GPU_QUEUE,
            "PDF_QUEUE": PDF_QUEUE,
        }

        print("Available queues:")
        for name, queue in queues.items():
            print(f"  ✅ {name}: {queue.name}")

        return True
    except Exception as e:
        print(f"❌ Queue test failed: {e}")
        return False


if __name__ == "__main__":
    print("🧪 Testing extralit-server queue configuration...")

    queue_test = test_pdf_queue()
    all_queues_test = test_all_queues()

    if queue_test and all_queues_test:
        print("\n🎉 All queue tests passed!")
    else:
        print("\n💥 Some queue tests failed!")
