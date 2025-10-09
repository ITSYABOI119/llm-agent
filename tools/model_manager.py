"""
Smart Model Manager - Handle model loading and swapping
Optimized for Windows + Ollama (2.5s swap time reality)
"""

import logging
import requests
import time
from typing import Dict, Optional, List


class SmartModelManager:
    """
    Manages model loading with accurate swap time measurement

    Reality Check (Windows):
    - Model swaps take ~2.5s (disk → VRAM, unavoidable)
    - RAM preloading doesn't work reliably on Windows
    - Strategy: Minimize swaps through intelligent routing (Phase 2)
    """

    def __init__(self, api_url: str, config: Dict[str, Any]) -> None:
        self.api_url = api_url
        self.config = config
        self.current_vram_model: Optional[str] = None

        # Get keep_alive setting (default: 60 minutes)
        self.keep_alive = config.get('ollama', {}).get('keep_alive', '60m')

        # Model configuration
        self.models = {
            'context_master': 'openthinker3-7b',  # Planning & reasoning
            'executor': 'qwen2.5-coder:7b',       # Fast code generation
            'fixer': 'deepseek-r1:14b'            # Emergency debugging
        }

        # Swap statistics
        self.swap_count = 0
        self.total_swap_time = 0.0

    def ensure_in_vram(self, model: str, phase: Optional[str] = None) -> bool:
        """
        Ensure model is loaded in VRAM

        IMPORTANT: Actually loads the model with API call
        This measures real swap time (~2.5s on Windows)
        """
        if self.current_vram_model == model:
            # Already loaded, no swap needed
            logging.debug(f"{model} already in VRAM")
            return True

        # Need to swap models
        phase_str = f" for {phase}" if phase else ""
        logging.info(f"Loading {model} to VRAM{phase_str}...")
        start_time = time.time()

        try:
            # Actually load the model with minimal inference
            # This forces Ollama to load the model into VRAM
            response = requests.post(
                f"{self.api_url}/api/generate",
                json={
                    "model": model,
                    "prompt": "",
                    "keep_alive": self.keep_alive,
                    "stream": False,
                    "options": {"num_predict": 0}  # Just load, no inference
                },
                timeout=30
            )

            elapsed = time.time() - start_time

            if response.status_code == 200:
                # Update tracking
                self.current_vram_model = model
                self.swap_count += 1
                self.total_swap_time += elapsed

                logging.info(f"[OK] Model loaded in {elapsed:.2f}s (swap #{self.swap_count})")
                return True
            else:
                logging.error(f"[FAIL] Model load failed: HTTP {response.status_code}")
                return False

        except Exception as e:
            elapsed = time.time() - start_time
            logging.error(f"[FAIL] Model load error after {elapsed:.2f}s: {e}")
            return False

    def smart_load_for_phase(self, phase: str) -> str:
        """
        Load appropriate model for workflow phase

        Phases:
        - context: OpenThinker (gather context, understand task)
        - planning: OpenThinker (create detailed plan)
        - execution: Qwen (fast code generation)
        - verification: OpenThinker (check if it worked)
        - debugging: DeepSeek (emergency fixes)
        """
        model_map = {
            'context': self.models['context_master'],
            'planning': self.models['context_master'],
            'execution': self.models['executor'],
            'verification': self.models['context_master'],
            'debugging': self.models['fixer']
        }

        model = model_map.get(phase, self.models['context_master'])
        self.ensure_in_vram(model, phase)
        return model

    def refresh_keep_alive(self, model: str) -> None:
        """
        Refresh keep_alive timer to keep model loaded longer
        Note: On Windows, models still evict on swap despite this
        """
        try:
            requests.post(
                f"{self.api_url}/api/generate",
                json={
                    "model": model,
                    "prompt": "",
                    "keep_alive": self.keep_alive,
                    "options": {"num_predict": 0}
                },
                timeout=5
            )
            logging.debug(f"Refreshed keep_alive for {model}")
        except Exception as e:
            logging.debug(f"Could not refresh keep_alive: {e}")

    def get_model_for_role(self, role: str) -> str:
        """Get model name by role"""
        return self.models.get(role, self.models['context_master'])

    def get_status(self) -> Dict:
        """Get current model status and statistics"""
        avg_swap_time = (
            self.total_swap_time / self.swap_count
            if self.swap_count > 0 else 0.0
        )

        return {
            'vram_model': self.current_vram_model,
            'keep_alive': self.keep_alive,
            'models': self.models,
            'swap_count': self.swap_count,
            'total_swap_time': f"{self.total_swap_time:.2f}s",
            'avg_swap_time': f"{avg_swap_time:.2f}s"
        }

    def call_model(self, model: str, prompt: str, **kwargs) -> Dict:
        """
        Call a model with automatic VRAM management

        Args:
            model: Model name
            prompt: Prompt to send
            **kwargs: Additional options

        Returns:
            API response dict
        """
        # Ensure model is loaded (may trigger swap)
        if not self.ensure_in_vram(model):
            return {
                'success': False,
                'error': 'Failed to load model',
                'model': model
            }

        # Make request
        try:
            response = requests.post(
                f"{self.api_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "keep_alive": self.keep_alive,
                    "stream": False,
                    **kwargs
                },
                timeout=kwargs.get('timeout', 120)
            )

            if response.status_code == 200:
                return {
                    'success': True,
                    'response': response.json().get('response', ''),
                    'model': model
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}",
                    'model': model
                }

        except Exception as e:
            logging.error(f"Model call failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'model': model
            }

    def get_swap_report(self) -> str:
        """Get detailed swap statistics report"""
        status = self.get_status()

        report = f"""
Model Manager Statistics
========================
Current VRAM model: {status['vram_model'] or 'None'}
Keep alive setting: {status['keep_alive']}

Swap Statistics:
  Total swaps:     {status['swap_count']}
  Total time:      {status['total_swap_time']}
  Average time:    {status['avg_swap_time']}

Available Models:
  Context/Planning: {self.models['context_master']}
  Execution:        {self.models['executor']}
  Debugging/Fixer:  {self.models['fixer']}

Note: Model swaps take ~2.5s on Windows (disk → VRAM)
      Phase 2 will minimize swaps through intelligent routing
"""
        return report
