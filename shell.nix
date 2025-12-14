with import <nixpkgs> { };

let
  pythonPackages = python3Packages;
in pkgs.mkShell {
  buildInputs = [
    pythonPackages.python

    # Core dependencies
    pythonPackages.pip
    pythonPackages.pandas
    pythonPackages.beautifulsoup4
    pythonPackages.requests
    pythonPackages.lxml
    pythonPackages.tqdm
    pythonPackages.odfpy
    pythonPackages.openpyxl

    # Development tools
    prek
    ruff  # Fast Python linter and formatter (replaces black, flake8, isort)
    pythonPackages.pytest
    pythonPackages.pytest-cov
    pythonPackages.pytest-mock
    pythonPackages.mypy
  ];

  shellHook = ''
    # Set up pre-commit hooks on first entry
    if [ ! -d .git/hooks ]; then
      echo "Installing pre-commit hooks..."
      pre-commit install --install-hooks
    fi

    echo "Steam Stats development environment loaded"
    echo "Python version: $(python --version)"
    echo "Pre-commit available: $(pre-commit --version)"
  '';
}
