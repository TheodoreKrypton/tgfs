module.exports = {
  moduleFileExtensions: ['js', 'json', 'ts'],
  rootDir: '.',
  setupFiles: ['<rootDir>/test/utils/mock-tg-client.ts'],
  testRegex: '.*\\.spec\\.(t|j)s$',
  transform: {
    '^.+\\.(t|j)s$': 'ts-jest',
  },
  collectCoverageFrom: ['src/**/*.(t|j)s'],
  coverageDirectory: './coverage',
  testEnvironment: 'node',
  moduleNameMapper: {
    '^~test/(.*)': '<rootDir>/test/$1',
    '^~/(.*)': '<rootDir>/src/$1',
    '^src/(.*)': '<rootDir>/src/$1',
  },
  roots: ['<rootDir>'],
  moduleDirectories: ['node_modules'],
  // Needed for memory leak issue with NodeJS 16. See https://github.com/facebook/jest/issues/11956
  workerIdleMemoryLimit: '50M',
};
