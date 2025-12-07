#!/usr/bin/env python3
"""
Test script for LLM Provider Wrapper

Tests all three providers (OpenAI, Anthropic, Google) with different models.
Verifies that the wrapper correctly switches between providers.

Usage:
    python test_llm.py                    # Test all providers
    python test_llm.py --invoke           # Test with actual API calls
    python test_llm.py --provider openai  # Test specific provider
"""

import asyncio
import argparse
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app.services.llm import get_llm, get_llm_config


def test_provider_initialization():
    """Test that all providers can be initialized."""
    print("=" * 60)
    print("🧪 Testing Provider Initialization")
    print("=" * 60)
    
    providers = {
        "openai": ["gpt-4o", "gpt-5"],
        "anthropic": ["claude-sonnet-4.5"],
        "google": ["gemini-2.5-pro", "gemini-3-pro-preview"],
    }
    
    for provider, models in providers.items():
        print(f"\n📦 Testing {provider.upper()}")
        
        # Check if API key is available
        api_key_vars = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY"
        }
        
        api_key = os.getenv(api_key_vars[provider])
        if not api_key:
            print(f"   ⚠️  No API key found ({api_key_vars[provider]}), skipping")
            continue
        
        for model in models:
            try:
                llm = get_llm(provider=provider, model=model)
                llm_type = type(llm).__name__
                print(f"   ✅ {model}: {llm_type}")
            except Exception as e:
                print(f"   ❌ {model}: {str(e)[:50]}")


def test_environment_config():
    """Test configuration from environment variables."""
    print("\n" + "=" * 60)
    print("🔧 Testing Environment Configuration")
    print("=" * 60)
    
    config = get_llm_config()
    print(f"\nCurrent configuration:")
    print(f"  Provider: {config['provider']}")
    print(f"  Model: {config['model']}")
    print(f"  Temperature: {config['temperature']}")
    
    try:
        llm = get_llm()
        print(f"\n✅ LLM initialized: {type(llm).__name__}")
    except Exception as e:
        print(f"\n❌ Failed to initialize: {e}")


async def test_invocation(provider: str = None):
    """Test actual API invocation with a simple prompt."""
    print("\n" + "=" * 60)
    print("💬 Testing API Invocation")
    print("=" * 60)
    
    # Determine which provider to test
    if provider:
        providers_to_test = [provider]
    else:
        # Test all providers that have API keys
        providers_to_test = []
        if os.getenv("OPENAI_API_KEY"):
            providers_to_test.append("openai")
        if os.getenv("ANTHROPIC_API_KEY"):
            providers_to_test.append("anthropic")
        if os.getenv("GOOGLE_API_KEY"):
            providers_to_test.append("google")
    
    test_prompt = "Say 'Hello from Coastline!' in exactly 5 words."
    
    for prov in providers_to_test:
        print(f"\n🤖 Testing {prov.upper()}")
        
        try:
            llm = get_llm(provider=prov)
            
            # Invoke the LLM
            print(f"   Prompt: {test_prompt}")
            print(f"   Generating...", end=" ", flush=True)
            
            response = await llm.ainvoke(test_prompt)
            print("Done!")
            
            # Display response
            content = response.content if hasattr(response, 'content') else str(response)
            print(f"   Response: {content}")
            print(f"   ✅ {prov.capitalize()} working!")
            
        except Exception as e:
            print(f"\n   ❌ {prov.capitalize()} failed: {str(e)}")


def test_temperature_settings():
    """Test different temperature settings."""
    print("\n" + "=" * 60)
    print("🌡️  Testing Temperature Settings")
    print("=" * 60)
    
    temperatures = [0, 0.5, 1.0]
    
    for temp in temperatures:
        try:
            llm = get_llm(temperature=temp)
            print(f"✅ Temperature {temp}: {type(llm).__name__}")
        except Exception as e:
            print(f"❌ Temperature {temp}: {str(e)[:50]}")


def print_summary():
    """Print a helpful summary."""
    print("\n" + "=" * 60)
    print("📋 Summary")
    print("=" * 60)
    print("\nTo switch providers, set environment variables in .env:")
    print("\n  # Use OpenAI (default)")
    print("  LLM_PROVIDER=openai")
    print("  LLM_MODEL=gpt-5")
    print("  OPENAI_API_KEY=sk-...")
    print("\n  # Use Anthropic")
    print("  LLM_PROVIDER=anthropic")
    print("  LLM_MODEL=claude-sonnet-4")
    print("  ANTHROPIC_API_KEY=sk-ant-...")
    print("\n  # Use Google")
    print("  LLM_PROVIDER=google")
    print("  LLM_MODEL=gemini-3-pro-preview")
    print("  GOOGLE_API_KEY=...")
    print()


async def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="Test LLM Provider Wrapper")
    parser.add_argument(
        "--invoke",
        action="store_true",
        help="Test with actual API calls (requires API keys)"
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "anthropic", "google"],
        help="Test specific provider only"
    )
    args = parser.parse_args()
    
    print("\n🌊 Coastline LLM Provider Wrapper Tests\n")
    
    # Run tests
    test_environment_config()
    test_provider_initialization()
    test_temperature_settings()
    
    if args.invoke:
        await test_invocation(provider=args.provider)
    else:
        print("\n💡 Tip: Use --invoke to test actual API calls")
    
    print_summary()


if __name__ == "__main__":
    asyncio.run(main())

