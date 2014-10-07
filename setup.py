from setuptools import setup

# Setup definitions
setup(
    name="python-tinylink",
    version="1.1",
    description="Frame-based streaming protocol for embedded applications.",
    author="Bas Stottelaar",
    author_email="basstottelaar@gmail.com",
    py_modules=["tinylink"],
    license = "MIT",
    keywords = "python embedded arm arduino tinylink streaming serial",
    test_suite="tests",
    entry_points={
        "console_scripts": [
            "tinylink = tinylink.cli:run",
        ]
    },
    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Topic :: System :: Networking",
        "Topic :: Software Development :: Embedded Systems",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
    ],
)