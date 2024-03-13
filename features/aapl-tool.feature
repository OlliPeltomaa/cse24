Feature: AAPL off-market trade tool

  Scenario: Successful database initialization
    Given the system is starting
    When the application initializes
    Then the three database tables should be created

  Scenario: Fetching stock market data
    Given the system is running
    When a request is made to fetch stock market data
    Then the system should retrieve and return the latest stock market data

  Scenario: Client places a bid with non-valid price and quantity, but no matching offers
    Given the system is running and has stock market data available
    When the user places a bid with non-valid values
    Then the bid should be ignored

  Scenario: Client places a bid with valid price and quantity, but no matching offers
    Given the system is running and has stock market data available
    When the user places a bid with valid values
    Then the bid should be stored in the system

