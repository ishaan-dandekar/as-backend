import re
from collections import Counter


POPULAR_SKILL_TAGS = [
    'JavaScript',
    'TypeScript',
    'Python',
    'Java',
    'C++',
    'C',
    'C#',
    'Go',
    'Rust',
    'PHP',
    'Ruby',
    'Kotlin',
    'Swift',
    'Dart',
    'React',
    'Next.js',
    'Node.js',
    'Express',
    'Django',
    'Flask',
    'FastAPI',
    'Spring Boot',
    'Angular',
    'Vue.js',
    'Tailwind CSS',
    'HTML',
    'CSS',
    'PostgreSQL',
    'MySQL',
    'MongoDB',
    'Redis',
    'Firebase',
    'Supabase',
    'Docker',
    'Kubernetes',
    'AWS',
    'Azure',
    'GCP',
    'Git',
    'GitHub',
    'Linux',
    'GraphQL',
    'REST API',
    'TensorFlow',
    'PyTorch',
    'Pandas',
    'NumPy',
    'Machine Learning',
    'Data Structures',
    'DevOps',
]

SKILL_TAG_ALIASES = {
    'js': 'JavaScript',
    'javascript': 'JavaScript',
    'ts': 'TypeScript',
    'typescript': 'TypeScript',
    'py': 'Python',
    'python': 'Python',
    'java': 'Java',
    'c++': 'C++',
    'cpp': 'C++',
    'c': 'C',
    'c#': 'C#',
    'csharp': 'C#',
    'golang': 'Go',
    'go': 'Go',
    'rust': 'Rust',
    'php': 'PHP',
    'ruby': 'Ruby',
    'kotlin': 'Kotlin',
    'swift': 'Swift',
    'dart': 'Dart',
    'react': 'React',
    'reactjs': 'React',
    'react.js': 'React',
    'next': 'Next.js',
    'nextjs': 'Next.js',
    'next.js': 'Next.js',
    'node': 'Node.js',
    'nodejs': 'Node.js',
    'node.js': 'Node.js',
    'express': 'Express',
    'django': 'Django',
    'flask': 'Flask',
    'fastapi': 'FastAPI',
    'spring': 'Spring Boot',
    'spring boot': 'Spring Boot',
    'angular': 'Angular',
    'vue': 'Vue.js',
    'vuejs': 'Vue.js',
    'vue.js': 'Vue.js',
    'tailwind': 'Tailwind CSS',
    'tailwindcss': 'Tailwind CSS',
    'tailwind css': 'Tailwind CSS',
    'html': 'HTML',
    'css': 'CSS',
    'postgres': 'PostgreSQL',
    'postgresql': 'PostgreSQL',
    'mysql': 'MySQL',
    'mongodb': 'MongoDB',
    'mongo': 'MongoDB',
    'redis': 'Redis',
    'firebase': 'Firebase',
    'supabase': 'Supabase',
    'docker': 'Docker',
    'k8s': 'Kubernetes',
    'kubernetes': 'Kubernetes',
    'aws': 'AWS',
    'azure': 'Azure',
    'gcp': 'GCP',
    'git': 'Git',
    'github': 'GitHub',
    'linux': 'Linux',
    'graphql': 'GraphQL',
    'rest': 'REST API',
    'rest api': 'REST API',
    'restful api': 'REST API',
    'tensorflow': 'TensorFlow',
    'pytorch': 'PyTorch',
    'pandas': 'Pandas',
    'numpy': 'NumPy',
    'ml': 'Machine Learning',
    'machine learning': 'Machine Learning',
    'data structures': 'Data Structures',
    'dsa': 'Data Structures',
    'devops': 'DevOps',
}

_SPECIAL_SKILL_CASES = {'AI', 'ML', 'AWS', 'GCP', 'HTML', 'CSS', 'SQL', 'UI', 'UX', 'API'}


PROJECT_DOMAIN_RULES = {
    'AI/ML': ['ai', 'ml', 'machine learning', 'deep learning', 'llm', 'nlp', 'computer vision', 'neural'],
    'Web Development': ['web', 'frontend', 'backend', 'full stack', 'react', 'next.js', 'django', 'flask', 'node'],
    'Mobile App': ['mobile', 'android', 'ios', 'flutter', 'react native', 'app'],
    'Data Science': ['data science', 'analytics', 'visualization', 'pandas', 'numpy', 'power bi', 'dashboard'],
    'IoT/Embedded': ['iot', 'embedded', 'arduino', 'raspberry pi', 'sensor', 'hardware'],
    'Cybersecurity': ['cybersecurity', 'security', 'encryption', 'authentication', 'authorization', 'threat'],
    'Cloud/DevOps': ['cloud', 'devops', 'docker', 'kubernetes', 'aws', 'azure', 'gcp', 'deployment', 'ci/cd'],
    'Blockchain': ['blockchain', 'web3', 'smart contract', 'ethereum', 'solidity'],
    'EdTech': ['education', 'student', 'learning', 'campus', 'classroom', 'course'],
    'HealthTech': ['health', 'medical', 'patient', 'hospital', 'wellness'],
    'FinTech': ['finance', 'payment', 'banking', 'trading', 'fintech', 'wallet'],
    'E-Commerce': ['ecommerce', 'e-commerce', 'shopping', 'cart', 'marketplace', 'store'],
    'Social Platform': ['social', 'community', 'chat', 'messaging', 'network'],
}

TEAM_KEYWORD_STOPWORDS = {
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'build', 'building', 'by', 'for', 'from', 'in',
    'into', 'is', 'of', 'on', 'our', 'team', 'the', 'their', 'this', 'to', 'we', 'with', 'you',
    'your', 'looking', 'need', 'needs', 'want', 'who', 'will',
}


def normalize_skill_tag(value):
    item = re.sub(r'\s+', ' ', str(value or '').strip())
    if not item:
        return ''

    alias_match = SKILL_TAG_ALIASES.get(item.lower())
    if alias_match:
        return alias_match

    tokens = []
    for token in item.split(' '):
        upper_token = token.upper()
        if upper_token in _SPECIAL_SKILL_CASES:
            tokens.append(upper_token)
        elif any(char in token for char in ['.', '#', '+']) or any(char.isupper() for char in token[1:]):
            tokens.append(token)
        else:
            tokens.append(token.capitalize())

    return ' '.join(tokens)


def normalize_tags(values):
    seen = set()
    normalized = []

    for value in values or []:
        item = normalize_skill_tag(value)
        if not item:
            continue

        key = item.lower()
        if key in seen:
            continue

        seen.add(key)
        normalized.append(item)

    return normalized


def infer_project_domains(title='', description='', tech_stack=None):
    joined_text = ' '.join([
        str(title or ''),
        str(description or ''),
        ' '.join(str(item or '') for item in (tech_stack or [])),
    ]).lower()

    matched_domains = []
    for domain, keywords in PROJECT_DOMAIN_RULES.items():
        if any(keyword in joined_text for keyword in keywords):
            matched_domains.append(domain)

    if matched_domains:
        return matched_domains

    tech_tokens = normalize_tags(tech_stack or [])
    if tech_tokens:
        return tech_tokens[:3]

    fallback_tokens = re.findall(r'[a-z0-9]{4,}', joined_text)
    return [token.title() for token in fallback_tokens[:3]]


def extract_team_search_keywords(name='', description=''):
    text = f'{name or ""} {description or ""}'.lower()
    tokens = re.findall(r'[a-z0-9][a-z0-9.+#-]{2,}', text)

    counts = Counter(
        token for token in tokens
        if token not in TEAM_KEYWORD_STOPWORDS and not token.isdigit()
    )

    ranked_tokens = [
        token
        for token, _ in counts.most_common(16)
    ]

    return normalize_tags(ranked_tokens)
