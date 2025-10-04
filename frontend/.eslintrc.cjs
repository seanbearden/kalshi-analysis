// Legacy ESLint config for pre-commit hooks
// The main config is in eslint.config.js (flat config)
module.exports = {
  root: true,
  env: { browser: true, es2020: true },
  extends: [
    'eslint:recommended',
  ],
  ignorePatterns: ['dist', '.eslintrc.cjs', 'node_modules', 'coverage'],
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 2020,
    sourceType: 'module',
  },
  rules: {
    // Minimal rules to avoid version conflicts
    'no-unused-vars': 'off', // Handled by TypeScript
    'no-undef': 'off', // Handled by TypeScript
  },
}
