module.exports = {
  verbose: true,
  testRegex: '.*\\.spec\\.(t|j)s$',
  coverageDirectory: './coverage',
  moduleFileExtensions: ['ts', 'js'],
  collectCoverageFrom: ['src/**'],
  transform: {
    '^.+\\.(t|j)s$': [
      'ts-jest',
      {
        tsconfig: {
          sourceMap: false,
        },
      },
    ],
  },
};
