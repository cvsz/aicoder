import os
import re

# Mapping of file prefixes to directories
mapping = {
    'claude_advisor': 'agents',
    'claude_agents_sdk': 'agents',
    'claude_eval': 'agents',
    'claude_evals': 'agents',
    'claude_fable5': 'agents',
    'claude_github': 'agents',
    'claude_git': 'agents',
    'claude_live': 'agents',
    'claude_mythos5': 'agents',
    'claude_rag': 'agents',
    'claude_research': 'agents',
    'claude_router': 'agents',
    'claude_sessions': 'agents',
    'claude_workflow': 'agents',
    'cowork': 'agents',
    'claude_batch': 'api',
    'claude_cache': 'api',
    'claude_citations': 'api',
    'claude_files': 'api',
    'claude_models': 'api',
    'claude_search': 'api',
    'claude_stream': 'api',
    'claude_structured': 'api',
    'claude_vision': 'api',
    'claude_code_exec': 'core',
    'claude_code': 'core',
    'claude_hooks_perms_plan': 'core',
    'claude_memory': 'core',
    'claude_output_styles': 'core',
    'claude_plugins': 'core',
    'claude_prompt_optimizer': 'core',
    'claude_sandbox': 'core',
    'claude_settings': 'core',
    'claude_thinking': 'core',
    'claude_tools': 'core',
    'coder': 'core',
    'config': 'core',
    'personalities': 'core',
    'projects': 'core',
    'skills': 'core',
    'utils': 'core',
    'claude_cost_optimizer': 'utils',
    'claude_embeddings': 'utils',
    'claude_metrics': 'utils',
    'claude_observability': 'utils',
    'claude_tokens': 'utils',
}

def update_imports(file_path):
    with open(file_path, 'r') as f:
        content = f.read()

    new_content = content
    for name, directory in mapping.items():
        # Find imports of the form 'from claude_x import ...' or 'import claude_x'
        # The goal is to change them to 'from directory.claude_x import ...'
        # or 'import directory.claude_x as claude_x'
        
        # Simple regex for 'from claude_x' -> 'from directory.claude_x'
        # This handles cases where file is in root and now in subfolder
        # Note: Need to be careful not to double-replace if already updated.
        
        # Matches: from claude_x ...
        pattern_from = rf'from\s+{name}\s+'
        replacement_from = f'from {directory}.{name} '
        new_content = re.sub(pattern_from, replacement_from, new_content)
        
        # Matches: import claude_x
        # For simplicity, if it's already structured, this script might need to skip.
        # But based on the grep, most are 'from claude_...'.
        
    if new_content != content:
        with open(file_path, 'w') as f:
            f.write(new_content)
        print(f"Updated: {file_path}")

for root, dirs, files in os.walk('.'):
    for file in files:
        if file.endswith('.py') and file != 'scripts/update_imports.py':
            update_imports(os.path.join(root, file))
