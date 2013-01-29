# creole-parser

Python 3.2 Creole wiki markup parser.

- Processes wiki markup text in a single-pass.
- Does not use regular expression substitution.
- Does not require any other modules.

## Introduction

This module parses Cerole wiki version 1.0 markup text into HTML5 or XHTML.
It only outputs HTML tags, not an entire document.  The parser output is
is intended for inclusion in the `<body>` or `<div>` section of a page.

This module requires Python 3 and has only been tested with version 3.2.

## Details

It provides the `CreoleParser` class that parses markup from a string or any object capable of producing lines of text from an iterator (files, etc.). It also provides the `parse()` function that instantiates the parser for applications where a simple function call is all that is required.

By default, the output is HTML5 text.  This means that tags such as `<br>`,
`<img>`, and `<hr>` are not output as self-closing tags.  The resulting HTML5
can be included in a document that having the text/html content type, but
not as an XHTML (or any XML) document.  If XHTML is required, the parser
can be instantiated with the `html5` parameter set to False.

Reference: <http://www.wikicreole.org/wiki/Creole1.0>

## Installation

Simply include the `creole_parser.py` module in your source tree and import it
as shown in the examples.

## Examples

### Example 1

Instantiating the CreoleParser class:

```python    
from creole_parser import CreoleParser

parser = CreoleParser()

file = open('markup.creole')
result = parser.parse(file)
file.close()

print(result.heading)   # can be None if no heading was found
print(result)           # the result is just a normal string
```

### Example 2

Calling the module-level parse() function:

```python
import creole_parser

file = open('markup.creole')
result = creole_parser.parse(file)
file.close()

print(result.heading)   # can be None if no heading was found
print(result)           # the result is just a normal string
```

## Differences

Differences between this implementation and the Creole 1.0 specification:

1. Supports the following additional markup:

        ^^superscript^^
        ,,subscript,,
        __underline__
        ; definition list term
        : definition list description

2. Consecutive table columns (`||`, `|=|=`, or any combination) are
   merged into a single `<th>` or `<td>` tag with the colspan attribute.
   The value of the last column indicator determines the type of tag
   so `||=` and `|=|=` both generate a `<th colspan="2">` tag.

3. Headings can have an id attribute.  This is useful for fragment
   links (e.g., #target) in a table of contents.  The id attribute
   is taken from the text following the last closing equal sign.
   For example, `== System Overview == overview` generates the
   following HTML: `<h2 id="overview">System Overview</h2>`.

4. Free-standing link URI schemes include 'http', 'https', and 'ftp'.
   The specification does not mention 'https'.  Also, it does not
   specify when a free-standing link ends.  The parser stops when
   it encounters a space, tab, or end-of-line.  It then applies the
   punctuation rules stated in the specification.

5. The Creole specification labels invalid nesting as unacceptable.
   It does not define what unacceptable means.  The parser does not
   raise an exception on invalid input.  It will always output valid
   HTML even if the input contains errors.

## Error Handling

Overall design philosophy: do not raise exceptions on invalid input input
(e.g., invalid nesting or unclosed links and images).  Always output what
was supplied.  If the input is invalid, then do not surround it with tags
and output the invalid text.  The author then sees what was, and was not,
parsed as valid markup because the text still appears, only not as HTML.

## Dependencies

The parser processes the wiki markup text in a single-pass without using
regular expression substitution.  It does not require any other modules.

## License (MIT)

Copyright (c) 2012 Frank Hellwig

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to
deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
sell copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
IN THE SOFTWARE.
