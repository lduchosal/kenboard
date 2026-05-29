(() => {
  var __create = Object.create;
  var __defProp = Object.defineProperty;
  var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
  var __getOwnPropNames = Object.getOwnPropertyNames;
  var __getProtoOf = Object.getPrototypeOf;
  var __hasOwnProp = Object.prototype.hasOwnProperty;
  var __commonJS = (cb, mod) => function __require() {
    return mod || (0, cb[__getOwnPropNames(cb)[0]])((mod = { exports: {} }).exports, mod), mod.exports;
  };
  var __copyProps = (to, from, except, desc) => {
    if (from && typeof from === "object" || typeof from === "function") {
      for (let key of __getOwnPropNames(from))
        if (!__hasOwnProp.call(to, key) && key !== except)
          __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
    }
    return to;
  };
  var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
    // If the importer is in node compatibility mode or this is not an ESM
    // file that has been converted to a CommonJS file using a Babel-
    // compatible transform (i.e. "__esModule" has not been set), then set
    // "default" to the CommonJS "module.exports" for node compatibility.
    isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
    mod
  ));

  // node_modules/diff-match-patch/index.js
  var require_diff_match_patch = __commonJS({
    "node_modules/diff-match-patch/index.js"(exports, module) {
      var diff_match_patch = function() {
        this.Diff_Timeout = 1;
        this.Diff_EditCost = 4;
        this.Match_Threshold = 0.5;
        this.Match_Distance = 1e3;
        this.Patch_DeleteThreshold = 0.5;
        this.Patch_Margin = 4;
        this.Match_MaxBits = 32;
      };
      var DIFF_DELETE = -1;
      var DIFF_INSERT = 1;
      var DIFF_EQUAL = 0;
      diff_match_patch.Diff = function(op, text) {
        return [op, text];
      };
      diff_match_patch.prototype.diff_main = function(text1, text2, opt_checklines, opt_deadline) {
        if (typeof opt_deadline == "undefined") {
          if (this.Diff_Timeout <= 0) {
            opt_deadline = Number.MAX_VALUE;
          } else {
            opt_deadline = (/* @__PURE__ */ new Date()).getTime() + this.Diff_Timeout * 1e3;
          }
        }
        var deadline = opt_deadline;
        if (text1 == null || text2 == null) {
          throw new Error("Null input. (diff_main)");
        }
        if (text1 == text2) {
          if (text1) {
            return [new diff_match_patch.Diff(DIFF_EQUAL, text1)];
          }
          return [];
        }
        if (typeof opt_checklines == "undefined") {
          opt_checklines = true;
        }
        var checklines = opt_checklines;
        var commonlength = this.diff_commonPrefix(text1, text2);
        var commonprefix = text1.substring(0, commonlength);
        text1 = text1.substring(commonlength);
        text2 = text2.substring(commonlength);
        commonlength = this.diff_commonSuffix(text1, text2);
        var commonsuffix = text1.substring(text1.length - commonlength);
        text1 = text1.substring(0, text1.length - commonlength);
        text2 = text2.substring(0, text2.length - commonlength);
        var diffs = this.diff_compute_(text1, text2, checklines, deadline);
        if (commonprefix) {
          diffs.unshift(new diff_match_patch.Diff(DIFF_EQUAL, commonprefix));
        }
        if (commonsuffix) {
          diffs.push(new diff_match_patch.Diff(DIFF_EQUAL, commonsuffix));
        }
        this.diff_cleanupMerge(diffs);
        return diffs;
      };
      diff_match_patch.prototype.diff_compute_ = function(text1, text2, checklines, deadline) {
        var diffs;
        if (!text1) {
          return [new diff_match_patch.Diff(DIFF_INSERT, text2)];
        }
        if (!text2) {
          return [new diff_match_patch.Diff(DIFF_DELETE, text1)];
        }
        var longtext = text1.length > text2.length ? text1 : text2;
        var shorttext = text1.length > text2.length ? text2 : text1;
        var i = longtext.indexOf(shorttext);
        if (i != -1) {
          diffs = [
            new diff_match_patch.Diff(DIFF_INSERT, longtext.substring(0, i)),
            new diff_match_patch.Diff(DIFF_EQUAL, shorttext),
            new diff_match_patch.Diff(
              DIFF_INSERT,
              longtext.substring(i + shorttext.length)
            )
          ];
          if (text1.length > text2.length) {
            diffs[0][0] = diffs[2][0] = DIFF_DELETE;
          }
          return diffs;
        }
        if (shorttext.length == 1) {
          return [
            new diff_match_patch.Diff(DIFF_DELETE, text1),
            new diff_match_patch.Diff(DIFF_INSERT, text2)
          ];
        }
        var hm = this.diff_halfMatch_(text1, text2);
        if (hm) {
          var text1_a = hm[0];
          var text1_b = hm[1];
          var text2_a = hm[2];
          var text2_b = hm[3];
          var mid_common = hm[4];
          var diffs_a = this.diff_main(text1_a, text2_a, checklines, deadline);
          var diffs_b = this.diff_main(text1_b, text2_b, checklines, deadline);
          return diffs_a.concat(
            [new diff_match_patch.Diff(DIFF_EQUAL, mid_common)],
            diffs_b
          );
        }
        if (checklines && text1.length > 100 && text2.length > 100) {
          return this.diff_lineMode_(text1, text2, deadline);
        }
        return this.diff_bisect_(text1, text2, deadline);
      };
      diff_match_patch.prototype.diff_lineMode_ = function(text1, text2, deadline) {
        var a = this.diff_linesToChars_(text1, text2);
        text1 = a.chars1;
        text2 = a.chars2;
        var linearray = a.lineArray;
        var diffs = this.diff_main(text1, text2, false, deadline);
        this.diff_charsToLines_(diffs, linearray);
        this.diff_cleanupSemantic(diffs);
        diffs.push(new diff_match_patch.Diff(DIFF_EQUAL, ""));
        var pointer = 0;
        var count_delete = 0;
        var count_insert = 0;
        var text_delete = "";
        var text_insert = "";
        while (pointer < diffs.length) {
          switch (diffs[pointer][0]) {
            case DIFF_INSERT:
              count_insert++;
              text_insert += diffs[pointer][1];
              break;
            case DIFF_DELETE:
              count_delete++;
              text_delete += diffs[pointer][1];
              break;
            case DIFF_EQUAL:
              if (count_delete >= 1 && count_insert >= 1) {
                diffs.splice(
                  pointer - count_delete - count_insert,
                  count_delete + count_insert
                );
                pointer = pointer - count_delete - count_insert;
                var subDiff = this.diff_main(text_delete, text_insert, false, deadline);
                for (var j = subDiff.length - 1; j >= 0; j--) {
                  diffs.splice(pointer, 0, subDiff[j]);
                }
                pointer = pointer + subDiff.length;
              }
              count_insert = 0;
              count_delete = 0;
              text_delete = "";
              text_insert = "";
              break;
          }
          pointer++;
        }
        diffs.pop();
        return diffs;
      };
      diff_match_patch.prototype.diff_bisect_ = function(text1, text2, deadline) {
        var text1_length = text1.length;
        var text2_length = text2.length;
        var max_d = Math.ceil((text1_length + text2_length) / 2);
        var v_offset = max_d;
        var v_length = 2 * max_d;
        var v1 = new Array(v_length);
        var v2 = new Array(v_length);
        for (var x = 0; x < v_length; x++) {
          v1[x] = -1;
          v2[x] = -1;
        }
        v1[v_offset + 1] = 0;
        v2[v_offset + 1] = 0;
        var delta = text1_length - text2_length;
        var front = delta % 2 != 0;
        var k1start = 0;
        var k1end = 0;
        var k2start = 0;
        var k2end = 0;
        for (var d = 0; d < max_d; d++) {
          if ((/* @__PURE__ */ new Date()).getTime() > deadline) {
            break;
          }
          for (var k1 = -d + k1start; k1 <= d - k1end; k1 += 2) {
            var k1_offset = v_offset + k1;
            var x1;
            if (k1 == -d || k1 != d && v1[k1_offset - 1] < v1[k1_offset + 1]) {
              x1 = v1[k1_offset + 1];
            } else {
              x1 = v1[k1_offset - 1] + 1;
            }
            var y1 = x1 - k1;
            while (x1 < text1_length && y1 < text2_length && text1.charAt(x1) == text2.charAt(y1)) {
              x1++;
              y1++;
            }
            v1[k1_offset] = x1;
            if (x1 > text1_length) {
              k1end += 2;
            } else if (y1 > text2_length) {
              k1start += 2;
            } else if (front) {
              var k2_offset = v_offset + delta - k1;
              if (k2_offset >= 0 && k2_offset < v_length && v2[k2_offset] != -1) {
                var x2 = text1_length - v2[k2_offset];
                if (x1 >= x2) {
                  return this.diff_bisectSplit_(text1, text2, x1, y1, deadline);
                }
              }
            }
          }
          for (var k2 = -d + k2start; k2 <= d - k2end; k2 += 2) {
            var k2_offset = v_offset + k2;
            var x2;
            if (k2 == -d || k2 != d && v2[k2_offset - 1] < v2[k2_offset + 1]) {
              x2 = v2[k2_offset + 1];
            } else {
              x2 = v2[k2_offset - 1] + 1;
            }
            var y2 = x2 - k2;
            while (x2 < text1_length && y2 < text2_length && text1.charAt(text1_length - x2 - 1) == text2.charAt(text2_length - y2 - 1)) {
              x2++;
              y2++;
            }
            v2[k2_offset] = x2;
            if (x2 > text1_length) {
              k2end += 2;
            } else if (y2 > text2_length) {
              k2start += 2;
            } else if (!front) {
              var k1_offset = v_offset + delta - k2;
              if (k1_offset >= 0 && k1_offset < v_length && v1[k1_offset] != -1) {
                var x1 = v1[k1_offset];
                var y1 = v_offset + x1 - k1_offset;
                x2 = text1_length - x2;
                if (x1 >= x2) {
                  return this.diff_bisectSplit_(text1, text2, x1, y1, deadline);
                }
              }
            }
          }
        }
        return [
          new diff_match_patch.Diff(DIFF_DELETE, text1),
          new diff_match_patch.Diff(DIFF_INSERT, text2)
        ];
      };
      diff_match_patch.prototype.diff_bisectSplit_ = function(text1, text2, x, y, deadline) {
        var text1a = text1.substring(0, x);
        var text2a = text2.substring(0, y);
        var text1b = text1.substring(x);
        var text2b = text2.substring(y);
        var diffs = this.diff_main(text1a, text2a, false, deadline);
        var diffsb = this.diff_main(text1b, text2b, false, deadline);
        return diffs.concat(diffsb);
      };
      diff_match_patch.prototype.diff_linesToChars_ = function(text1, text2) {
        var lineArray = [];
        var lineHash = {};
        lineArray[0] = "";
        function diff_linesToCharsMunge_(text) {
          var chars = "";
          var lineStart = 0;
          var lineEnd = -1;
          var lineArrayLength = lineArray.length;
          while (lineEnd < text.length - 1) {
            lineEnd = text.indexOf("\n", lineStart);
            if (lineEnd == -1) {
              lineEnd = text.length - 1;
            }
            var line = text.substring(lineStart, lineEnd + 1);
            if (lineHash.hasOwnProperty ? lineHash.hasOwnProperty(line) : lineHash[line] !== void 0) {
              chars += String.fromCharCode(lineHash[line]);
            } else {
              if (lineArrayLength == maxLines) {
                line = text.substring(lineStart);
                lineEnd = text.length;
              }
              chars += String.fromCharCode(lineArrayLength);
              lineHash[line] = lineArrayLength;
              lineArray[lineArrayLength++] = line;
            }
            lineStart = lineEnd + 1;
          }
          return chars;
        }
        var maxLines = 4e4;
        var chars1 = diff_linesToCharsMunge_(text1);
        maxLines = 65535;
        var chars2 = diff_linesToCharsMunge_(text2);
        return { chars1, chars2, lineArray };
      };
      diff_match_patch.prototype.diff_charsToLines_ = function(diffs, lineArray) {
        for (var i = 0; i < diffs.length; i++) {
          var chars = diffs[i][1];
          var text = [];
          for (var j = 0; j < chars.length; j++) {
            text[j] = lineArray[chars.charCodeAt(j)];
          }
          diffs[i][1] = text.join("");
        }
      };
      diff_match_patch.prototype.diff_commonPrefix = function(text1, text2) {
        if (!text1 || !text2 || text1.charAt(0) != text2.charAt(0)) {
          return 0;
        }
        var pointermin = 0;
        var pointermax = Math.min(text1.length, text2.length);
        var pointermid = pointermax;
        var pointerstart = 0;
        while (pointermin < pointermid) {
          if (text1.substring(pointerstart, pointermid) == text2.substring(pointerstart, pointermid)) {
            pointermin = pointermid;
            pointerstart = pointermin;
          } else {
            pointermax = pointermid;
          }
          pointermid = Math.floor((pointermax - pointermin) / 2 + pointermin);
        }
        return pointermid;
      };
      diff_match_patch.prototype.diff_commonSuffix = function(text1, text2) {
        if (!text1 || !text2 || text1.charAt(text1.length - 1) != text2.charAt(text2.length - 1)) {
          return 0;
        }
        var pointermin = 0;
        var pointermax = Math.min(text1.length, text2.length);
        var pointermid = pointermax;
        var pointerend = 0;
        while (pointermin < pointermid) {
          if (text1.substring(text1.length - pointermid, text1.length - pointerend) == text2.substring(text2.length - pointermid, text2.length - pointerend)) {
            pointermin = pointermid;
            pointerend = pointermin;
          } else {
            pointermax = pointermid;
          }
          pointermid = Math.floor((pointermax - pointermin) / 2 + pointermin);
        }
        return pointermid;
      };
      diff_match_patch.prototype.diff_commonOverlap_ = function(text1, text2) {
        var text1_length = text1.length;
        var text2_length = text2.length;
        if (text1_length == 0 || text2_length == 0) {
          return 0;
        }
        if (text1_length > text2_length) {
          text1 = text1.substring(text1_length - text2_length);
        } else if (text1_length < text2_length) {
          text2 = text2.substring(0, text1_length);
        }
        var text_length = Math.min(text1_length, text2_length);
        if (text1 == text2) {
          return text_length;
        }
        var best = 0;
        var length = 1;
        while (true) {
          var pattern = text1.substring(text_length - length);
          var found = text2.indexOf(pattern);
          if (found == -1) {
            return best;
          }
          length += found;
          if (found == 0 || text1.substring(text_length - length) == text2.substring(0, length)) {
            best = length;
            length++;
          }
        }
      };
      diff_match_patch.prototype.diff_halfMatch_ = function(text1, text2) {
        if (this.Diff_Timeout <= 0) {
          return null;
        }
        var longtext = text1.length > text2.length ? text1 : text2;
        var shorttext = text1.length > text2.length ? text2 : text1;
        if (longtext.length < 4 || shorttext.length * 2 < longtext.length) {
          return null;
        }
        var dmp = this;
        function diff_halfMatchI_(longtext2, shorttext2, i) {
          var seed = longtext2.substring(i, i + Math.floor(longtext2.length / 4));
          var j = -1;
          var best_common = "";
          var best_longtext_a, best_longtext_b, best_shorttext_a, best_shorttext_b;
          while ((j = shorttext2.indexOf(seed, j + 1)) != -1) {
            var prefixLength = dmp.diff_commonPrefix(
              longtext2.substring(i),
              shorttext2.substring(j)
            );
            var suffixLength = dmp.diff_commonSuffix(
              longtext2.substring(0, i),
              shorttext2.substring(0, j)
            );
            if (best_common.length < suffixLength + prefixLength) {
              best_common = shorttext2.substring(j - suffixLength, j) + shorttext2.substring(j, j + prefixLength);
              best_longtext_a = longtext2.substring(0, i - suffixLength);
              best_longtext_b = longtext2.substring(i + prefixLength);
              best_shorttext_a = shorttext2.substring(0, j - suffixLength);
              best_shorttext_b = shorttext2.substring(j + prefixLength);
            }
          }
          if (best_common.length * 2 >= longtext2.length) {
            return [
              best_longtext_a,
              best_longtext_b,
              best_shorttext_a,
              best_shorttext_b,
              best_common
            ];
          } else {
            return null;
          }
        }
        var hm1 = diff_halfMatchI_(
          longtext,
          shorttext,
          Math.ceil(longtext.length / 4)
        );
        var hm2 = diff_halfMatchI_(
          longtext,
          shorttext,
          Math.ceil(longtext.length / 2)
        );
        var hm;
        if (!hm1 && !hm2) {
          return null;
        } else if (!hm2) {
          hm = hm1;
        } else if (!hm1) {
          hm = hm2;
        } else {
          hm = hm1[4].length > hm2[4].length ? hm1 : hm2;
        }
        var text1_a, text1_b, text2_a, text2_b;
        if (text1.length > text2.length) {
          text1_a = hm[0];
          text1_b = hm[1];
          text2_a = hm[2];
          text2_b = hm[3];
        } else {
          text2_a = hm[0];
          text2_b = hm[1];
          text1_a = hm[2];
          text1_b = hm[3];
        }
        var mid_common = hm[4];
        return [text1_a, text1_b, text2_a, text2_b, mid_common];
      };
      diff_match_patch.prototype.diff_cleanupSemantic = function(diffs) {
        var changes = false;
        var equalities = [];
        var equalitiesLength = 0;
        var lastEquality = null;
        var pointer = 0;
        var length_insertions1 = 0;
        var length_deletions1 = 0;
        var length_insertions2 = 0;
        var length_deletions2 = 0;
        while (pointer < diffs.length) {
          if (diffs[pointer][0] == DIFF_EQUAL) {
            equalities[equalitiesLength++] = pointer;
            length_insertions1 = length_insertions2;
            length_deletions1 = length_deletions2;
            length_insertions2 = 0;
            length_deletions2 = 0;
            lastEquality = diffs[pointer][1];
          } else {
            if (diffs[pointer][0] == DIFF_INSERT) {
              length_insertions2 += diffs[pointer][1].length;
            } else {
              length_deletions2 += diffs[pointer][1].length;
            }
            if (lastEquality && lastEquality.length <= Math.max(length_insertions1, length_deletions1) && lastEquality.length <= Math.max(
              length_insertions2,
              length_deletions2
            )) {
              diffs.splice(
                equalities[equalitiesLength - 1],
                0,
                new diff_match_patch.Diff(DIFF_DELETE, lastEquality)
              );
              diffs[equalities[equalitiesLength - 1] + 1][0] = DIFF_INSERT;
              equalitiesLength--;
              equalitiesLength--;
              pointer = equalitiesLength > 0 ? equalities[equalitiesLength - 1] : -1;
              length_insertions1 = 0;
              length_deletions1 = 0;
              length_insertions2 = 0;
              length_deletions2 = 0;
              lastEquality = null;
              changes = true;
            }
          }
          pointer++;
        }
        if (changes) {
          this.diff_cleanupMerge(diffs);
        }
        this.diff_cleanupSemanticLossless(diffs);
        pointer = 1;
        while (pointer < diffs.length) {
          if (diffs[pointer - 1][0] == DIFF_DELETE && diffs[pointer][0] == DIFF_INSERT) {
            var deletion = diffs[pointer - 1][1];
            var insertion = diffs[pointer][1];
            var overlap_length1 = this.diff_commonOverlap_(deletion, insertion);
            var overlap_length2 = this.diff_commonOverlap_(insertion, deletion);
            if (overlap_length1 >= overlap_length2) {
              if (overlap_length1 >= deletion.length / 2 || overlap_length1 >= insertion.length / 2) {
                diffs.splice(pointer, 0, new diff_match_patch.Diff(
                  DIFF_EQUAL,
                  insertion.substring(0, overlap_length1)
                ));
                diffs[pointer - 1][1] = deletion.substring(0, deletion.length - overlap_length1);
                diffs[pointer + 1][1] = insertion.substring(overlap_length1);
                pointer++;
              }
            } else {
              if (overlap_length2 >= deletion.length / 2 || overlap_length2 >= insertion.length / 2) {
                diffs.splice(pointer, 0, new diff_match_patch.Diff(
                  DIFF_EQUAL,
                  deletion.substring(0, overlap_length2)
                ));
                diffs[pointer - 1][0] = DIFF_INSERT;
                diffs[pointer - 1][1] = insertion.substring(0, insertion.length - overlap_length2);
                diffs[pointer + 1][0] = DIFF_DELETE;
                diffs[pointer + 1][1] = deletion.substring(overlap_length2);
                pointer++;
              }
            }
            pointer++;
          }
          pointer++;
        }
      };
      diff_match_patch.prototype.diff_cleanupSemanticLossless = function(diffs) {
        function diff_cleanupSemanticScore_(one, two) {
          if (!one || !two) {
            return 6;
          }
          var char1 = one.charAt(one.length - 1);
          var char2 = two.charAt(0);
          var nonAlphaNumeric1 = char1.match(diff_match_patch.nonAlphaNumericRegex_);
          var nonAlphaNumeric2 = char2.match(diff_match_patch.nonAlphaNumericRegex_);
          var whitespace1 = nonAlphaNumeric1 && char1.match(diff_match_patch.whitespaceRegex_);
          var whitespace2 = nonAlphaNumeric2 && char2.match(diff_match_patch.whitespaceRegex_);
          var lineBreak1 = whitespace1 && char1.match(diff_match_patch.linebreakRegex_);
          var lineBreak2 = whitespace2 && char2.match(diff_match_patch.linebreakRegex_);
          var blankLine1 = lineBreak1 && one.match(diff_match_patch.blanklineEndRegex_);
          var blankLine2 = lineBreak2 && two.match(diff_match_patch.blanklineStartRegex_);
          if (blankLine1 || blankLine2) {
            return 5;
          } else if (lineBreak1 || lineBreak2) {
            return 4;
          } else if (nonAlphaNumeric1 && !whitespace1 && whitespace2) {
            return 3;
          } else if (whitespace1 || whitespace2) {
            return 2;
          } else if (nonAlphaNumeric1 || nonAlphaNumeric2) {
            return 1;
          }
          return 0;
        }
        var pointer = 1;
        while (pointer < diffs.length - 1) {
          if (diffs[pointer - 1][0] == DIFF_EQUAL && diffs[pointer + 1][0] == DIFF_EQUAL) {
            var equality1 = diffs[pointer - 1][1];
            var edit = diffs[pointer][1];
            var equality2 = diffs[pointer + 1][1];
            var commonOffset = this.diff_commonSuffix(equality1, edit);
            if (commonOffset) {
              var commonString = edit.substring(edit.length - commonOffset);
              equality1 = equality1.substring(0, equality1.length - commonOffset);
              edit = commonString + edit.substring(0, edit.length - commonOffset);
              equality2 = commonString + equality2;
            }
            var bestEquality1 = equality1;
            var bestEdit = edit;
            var bestEquality2 = equality2;
            var bestScore = diff_cleanupSemanticScore_(equality1, edit) + diff_cleanupSemanticScore_(edit, equality2);
            while (edit.charAt(0) === equality2.charAt(0)) {
              equality1 += edit.charAt(0);
              edit = edit.substring(1) + equality2.charAt(0);
              equality2 = equality2.substring(1);
              var score = diff_cleanupSemanticScore_(equality1, edit) + diff_cleanupSemanticScore_(edit, equality2);
              if (score >= bestScore) {
                bestScore = score;
                bestEquality1 = equality1;
                bestEdit = edit;
                bestEquality2 = equality2;
              }
            }
            if (diffs[pointer - 1][1] != bestEquality1) {
              if (bestEquality1) {
                diffs[pointer - 1][1] = bestEquality1;
              } else {
                diffs.splice(pointer - 1, 1);
                pointer--;
              }
              diffs[pointer][1] = bestEdit;
              if (bestEquality2) {
                diffs[pointer + 1][1] = bestEquality2;
              } else {
                diffs.splice(pointer + 1, 1);
                pointer--;
              }
            }
          }
          pointer++;
        }
      };
      diff_match_patch.nonAlphaNumericRegex_ = /[^a-zA-Z0-9]/;
      diff_match_patch.whitespaceRegex_ = /\s/;
      diff_match_patch.linebreakRegex_ = /[\r\n]/;
      diff_match_patch.blanklineEndRegex_ = /\n\r?\n$/;
      diff_match_patch.blanklineStartRegex_ = /^\r?\n\r?\n/;
      diff_match_patch.prototype.diff_cleanupEfficiency = function(diffs) {
        var changes = false;
        var equalities = [];
        var equalitiesLength = 0;
        var lastEquality = null;
        var pointer = 0;
        var pre_ins = false;
        var pre_del = false;
        var post_ins = false;
        var post_del = false;
        while (pointer < diffs.length) {
          if (diffs[pointer][0] == DIFF_EQUAL) {
            if (diffs[pointer][1].length < this.Diff_EditCost && (post_ins || post_del)) {
              equalities[equalitiesLength++] = pointer;
              pre_ins = post_ins;
              pre_del = post_del;
              lastEquality = diffs[pointer][1];
            } else {
              equalitiesLength = 0;
              lastEquality = null;
            }
            post_ins = post_del = false;
          } else {
            if (diffs[pointer][0] == DIFF_DELETE) {
              post_del = true;
            } else {
              post_ins = true;
            }
            if (lastEquality && (pre_ins && pre_del && post_ins && post_del || lastEquality.length < this.Diff_EditCost / 2 && pre_ins + pre_del + post_ins + post_del == 3)) {
              diffs.splice(
                equalities[equalitiesLength - 1],
                0,
                new diff_match_patch.Diff(DIFF_DELETE, lastEquality)
              );
              diffs[equalities[equalitiesLength - 1] + 1][0] = DIFF_INSERT;
              equalitiesLength--;
              lastEquality = null;
              if (pre_ins && pre_del) {
                post_ins = post_del = true;
                equalitiesLength = 0;
              } else {
                equalitiesLength--;
                pointer = equalitiesLength > 0 ? equalities[equalitiesLength - 1] : -1;
                post_ins = post_del = false;
              }
              changes = true;
            }
          }
          pointer++;
        }
        if (changes) {
          this.diff_cleanupMerge(diffs);
        }
      };
      diff_match_patch.prototype.diff_cleanupMerge = function(diffs) {
        diffs.push(new diff_match_patch.Diff(DIFF_EQUAL, ""));
        var pointer = 0;
        var count_delete = 0;
        var count_insert = 0;
        var text_delete = "";
        var text_insert = "";
        var commonlength;
        while (pointer < diffs.length) {
          switch (diffs[pointer][0]) {
            case DIFF_INSERT:
              count_insert++;
              text_insert += diffs[pointer][1];
              pointer++;
              break;
            case DIFF_DELETE:
              count_delete++;
              text_delete += diffs[pointer][1];
              pointer++;
              break;
            case DIFF_EQUAL:
              if (count_delete + count_insert > 1) {
                if (count_delete !== 0 && count_insert !== 0) {
                  commonlength = this.diff_commonPrefix(text_insert, text_delete);
                  if (commonlength !== 0) {
                    if (pointer - count_delete - count_insert > 0 && diffs[pointer - count_delete - count_insert - 1][0] == DIFF_EQUAL) {
                      diffs[pointer - count_delete - count_insert - 1][1] += text_insert.substring(0, commonlength);
                    } else {
                      diffs.splice(0, 0, new diff_match_patch.Diff(
                        DIFF_EQUAL,
                        text_insert.substring(0, commonlength)
                      ));
                      pointer++;
                    }
                    text_insert = text_insert.substring(commonlength);
                    text_delete = text_delete.substring(commonlength);
                  }
                  commonlength = this.diff_commonSuffix(text_insert, text_delete);
                  if (commonlength !== 0) {
                    diffs[pointer][1] = text_insert.substring(text_insert.length - commonlength) + diffs[pointer][1];
                    text_insert = text_insert.substring(0, text_insert.length - commonlength);
                    text_delete = text_delete.substring(0, text_delete.length - commonlength);
                  }
                }
                pointer -= count_delete + count_insert;
                diffs.splice(pointer, count_delete + count_insert);
                if (text_delete.length) {
                  diffs.splice(
                    pointer,
                    0,
                    new diff_match_patch.Diff(DIFF_DELETE, text_delete)
                  );
                  pointer++;
                }
                if (text_insert.length) {
                  diffs.splice(
                    pointer,
                    0,
                    new diff_match_patch.Diff(DIFF_INSERT, text_insert)
                  );
                  pointer++;
                }
                pointer++;
              } else if (pointer !== 0 && diffs[pointer - 1][0] == DIFF_EQUAL) {
                diffs[pointer - 1][1] += diffs[pointer][1];
                diffs.splice(pointer, 1);
              } else {
                pointer++;
              }
              count_insert = 0;
              count_delete = 0;
              text_delete = "";
              text_insert = "";
              break;
          }
        }
        if (diffs[diffs.length - 1][1] === "") {
          diffs.pop();
        }
        var changes = false;
        pointer = 1;
        while (pointer < diffs.length - 1) {
          if (diffs[pointer - 1][0] == DIFF_EQUAL && diffs[pointer + 1][0] == DIFF_EQUAL) {
            if (diffs[pointer][1].substring(diffs[pointer][1].length - diffs[pointer - 1][1].length) == diffs[pointer - 1][1]) {
              diffs[pointer][1] = diffs[pointer - 1][1] + diffs[pointer][1].substring(0, diffs[pointer][1].length - diffs[pointer - 1][1].length);
              diffs[pointer + 1][1] = diffs[pointer - 1][1] + diffs[pointer + 1][1];
              diffs.splice(pointer - 1, 1);
              changes = true;
            } else if (diffs[pointer][1].substring(0, diffs[pointer + 1][1].length) == diffs[pointer + 1][1]) {
              diffs[pointer - 1][1] += diffs[pointer + 1][1];
              diffs[pointer][1] = diffs[pointer][1].substring(diffs[pointer + 1][1].length) + diffs[pointer + 1][1];
              diffs.splice(pointer + 1, 1);
              changes = true;
            }
          }
          pointer++;
        }
        if (changes) {
          this.diff_cleanupMerge(diffs);
        }
      };
      diff_match_patch.prototype.diff_xIndex = function(diffs, loc) {
        var chars1 = 0;
        var chars2 = 0;
        var last_chars1 = 0;
        var last_chars2 = 0;
        var x;
        for (x = 0; x < diffs.length; x++) {
          if (diffs[x][0] !== DIFF_INSERT) {
            chars1 += diffs[x][1].length;
          }
          if (diffs[x][0] !== DIFF_DELETE) {
            chars2 += diffs[x][1].length;
          }
          if (chars1 > loc) {
            break;
          }
          last_chars1 = chars1;
          last_chars2 = chars2;
        }
        if (diffs.length != x && diffs[x][0] === DIFF_DELETE) {
          return last_chars2;
        }
        return last_chars2 + (loc - last_chars1);
      };
      diff_match_patch.prototype.diff_prettyHtml = function(diffs) {
        var html = [];
        var pattern_amp = /&/g;
        var pattern_lt = /</g;
        var pattern_gt = />/g;
        var pattern_para = /\n/g;
        for (var x = 0; x < diffs.length; x++) {
          var op = diffs[x][0];
          var data = diffs[x][1];
          var text = data.replace(pattern_amp, "&amp;").replace(pattern_lt, "&lt;").replace(pattern_gt, "&gt;").replace(pattern_para, "&para;<br>");
          switch (op) {
            case DIFF_INSERT:
              html[x] = '<ins style="background:#e6ffe6;">' + text + "</ins>";
              break;
            case DIFF_DELETE:
              html[x] = '<del style="background:#ffe6e6;">' + text + "</del>";
              break;
            case DIFF_EQUAL:
              html[x] = "<span>" + text + "</span>";
              break;
          }
        }
        return html.join("");
      };
      diff_match_patch.prototype.diff_text1 = function(diffs) {
        var text = [];
        for (var x = 0; x < diffs.length; x++) {
          if (diffs[x][0] !== DIFF_INSERT) {
            text[x] = diffs[x][1];
          }
        }
        return text.join("");
      };
      diff_match_patch.prototype.diff_text2 = function(diffs) {
        var text = [];
        for (var x = 0; x < diffs.length; x++) {
          if (diffs[x][0] !== DIFF_DELETE) {
            text[x] = diffs[x][1];
          }
        }
        return text.join("");
      };
      diff_match_patch.prototype.diff_levenshtein = function(diffs) {
        var levenshtein = 0;
        var insertions = 0;
        var deletions = 0;
        for (var x = 0; x < diffs.length; x++) {
          var op = diffs[x][0];
          var data = diffs[x][1];
          switch (op) {
            case DIFF_INSERT:
              insertions += data.length;
              break;
            case DIFF_DELETE:
              deletions += data.length;
              break;
            case DIFF_EQUAL:
              levenshtein += Math.max(insertions, deletions);
              insertions = 0;
              deletions = 0;
              break;
          }
        }
        levenshtein += Math.max(insertions, deletions);
        return levenshtein;
      };
      diff_match_patch.prototype.diff_toDelta = function(diffs) {
        var text = [];
        for (var x = 0; x < diffs.length; x++) {
          switch (diffs[x][0]) {
            case DIFF_INSERT:
              text[x] = "+" + encodeURI(diffs[x][1]);
              break;
            case DIFF_DELETE:
              text[x] = "-" + diffs[x][1].length;
              break;
            case DIFF_EQUAL:
              text[x] = "=" + diffs[x][1].length;
              break;
          }
        }
        return text.join("	").replace(/%20/g, " ");
      };
      diff_match_patch.prototype.diff_fromDelta = function(text1, delta) {
        var diffs = [];
        var diffsLength = 0;
        var pointer = 0;
        var tokens = delta.split(/\t/g);
        for (var x = 0; x < tokens.length; x++) {
          var param = tokens[x].substring(1);
          switch (tokens[x].charAt(0)) {
            case "+":
              try {
                diffs[diffsLength++] = new diff_match_patch.Diff(DIFF_INSERT, decodeURI(param));
              } catch (ex) {
                throw new Error("Illegal escape in diff_fromDelta: " + param);
              }
              break;
            case "-":
            // Fall through.
            case "=":
              var n = parseInt(param, 10);
              if (isNaN(n) || n < 0) {
                throw new Error("Invalid number in diff_fromDelta: " + param);
              }
              var text = text1.substring(pointer, pointer += n);
              if (tokens[x].charAt(0) == "=") {
                diffs[diffsLength++] = new diff_match_patch.Diff(DIFF_EQUAL, text);
              } else {
                diffs[diffsLength++] = new diff_match_patch.Diff(DIFF_DELETE, text);
              }
              break;
            default:
              if (tokens[x]) {
                throw new Error("Invalid diff operation in diff_fromDelta: " + tokens[x]);
              }
          }
        }
        if (pointer != text1.length) {
          throw new Error("Delta length (" + pointer + ") does not equal source text length (" + text1.length + ").");
        }
        return diffs;
      };
      diff_match_patch.prototype.match_main = function(text, pattern, loc) {
        if (text == null || pattern == null || loc == null) {
          throw new Error("Null input. (match_main)");
        }
        loc = Math.max(0, Math.min(loc, text.length));
        if (text == pattern) {
          return 0;
        } else if (!text.length) {
          return -1;
        } else if (text.substring(loc, loc + pattern.length) == pattern) {
          return loc;
        } else {
          return this.match_bitap_(text, pattern, loc);
        }
      };
      diff_match_patch.prototype.match_bitap_ = function(text, pattern, loc) {
        if (pattern.length > this.Match_MaxBits) {
          throw new Error("Pattern too long for this browser.");
        }
        var s = this.match_alphabet_(pattern);
        var dmp = this;
        function match_bitapScore_(e, x) {
          var accuracy = e / pattern.length;
          var proximity = Math.abs(loc - x);
          if (!dmp.Match_Distance) {
            return proximity ? 1 : accuracy;
          }
          return accuracy + proximity / dmp.Match_Distance;
        }
        var score_threshold = this.Match_Threshold;
        var best_loc = text.indexOf(pattern, loc);
        if (best_loc != -1) {
          score_threshold = Math.min(match_bitapScore_(0, best_loc), score_threshold);
          best_loc = text.lastIndexOf(pattern, loc + pattern.length);
          if (best_loc != -1) {
            score_threshold = Math.min(match_bitapScore_(0, best_loc), score_threshold);
          }
        }
        var matchmask = 1 << pattern.length - 1;
        best_loc = -1;
        var bin_min, bin_mid;
        var bin_max = pattern.length + text.length;
        var last_rd;
        for (var d = 0; d < pattern.length; d++) {
          bin_min = 0;
          bin_mid = bin_max;
          while (bin_min < bin_mid) {
            if (match_bitapScore_(d, loc + bin_mid) <= score_threshold) {
              bin_min = bin_mid;
            } else {
              bin_max = bin_mid;
            }
            bin_mid = Math.floor((bin_max - bin_min) / 2 + bin_min);
          }
          bin_max = bin_mid;
          var start = Math.max(1, loc - bin_mid + 1);
          var finish = Math.min(loc + bin_mid, text.length) + pattern.length;
          var rd = Array(finish + 2);
          rd[finish + 1] = (1 << d) - 1;
          for (var j = finish; j >= start; j--) {
            var charMatch = s[text.charAt(j - 1)];
            if (d === 0) {
              rd[j] = (rd[j + 1] << 1 | 1) & charMatch;
            } else {
              rd[j] = (rd[j + 1] << 1 | 1) & charMatch | ((last_rd[j + 1] | last_rd[j]) << 1 | 1) | last_rd[j + 1];
            }
            if (rd[j] & matchmask) {
              var score = match_bitapScore_(d, j - 1);
              if (score <= score_threshold) {
                score_threshold = score;
                best_loc = j - 1;
                if (best_loc > loc) {
                  start = Math.max(1, 2 * loc - best_loc);
                } else {
                  break;
                }
              }
            }
          }
          if (match_bitapScore_(d + 1, loc) > score_threshold) {
            break;
          }
          last_rd = rd;
        }
        return best_loc;
      };
      diff_match_patch.prototype.match_alphabet_ = function(pattern) {
        var s = {};
        for (var i = 0; i < pattern.length; i++) {
          s[pattern.charAt(i)] = 0;
        }
        for (var i = 0; i < pattern.length; i++) {
          s[pattern.charAt(i)] |= 1 << pattern.length - i - 1;
        }
        return s;
      };
      diff_match_patch.prototype.patch_addContext_ = function(patch, text) {
        if (text.length == 0) {
          return;
        }
        if (patch.start2 === null) {
          throw Error("patch not initialized");
        }
        var pattern = text.substring(patch.start2, patch.start2 + patch.length1);
        var padding = 0;
        while (text.indexOf(pattern) != text.lastIndexOf(pattern) && pattern.length < this.Match_MaxBits - this.Patch_Margin - this.Patch_Margin) {
          padding += this.Patch_Margin;
          pattern = text.substring(
            patch.start2 - padding,
            patch.start2 + patch.length1 + padding
          );
        }
        padding += this.Patch_Margin;
        var prefix = text.substring(patch.start2 - padding, patch.start2);
        if (prefix) {
          patch.diffs.unshift(new diff_match_patch.Diff(DIFF_EQUAL, prefix));
        }
        var suffix = text.substring(
          patch.start2 + patch.length1,
          patch.start2 + patch.length1 + padding
        );
        if (suffix) {
          patch.diffs.push(new diff_match_patch.Diff(DIFF_EQUAL, suffix));
        }
        patch.start1 -= prefix.length;
        patch.start2 -= prefix.length;
        patch.length1 += prefix.length + suffix.length;
        patch.length2 += prefix.length + suffix.length;
      };
      diff_match_patch.prototype.patch_make = function(a, opt_b, opt_c) {
        var text1, diffs;
        if (typeof a == "string" && typeof opt_b == "string" && typeof opt_c == "undefined") {
          text1 = /** @type {string} */
          a;
          diffs = this.diff_main(
            text1,
            /** @type {string} */
            opt_b,
            true
          );
          if (diffs.length > 2) {
            this.diff_cleanupSemantic(diffs);
            this.diff_cleanupEfficiency(diffs);
          }
        } else if (a && typeof a == "object" && typeof opt_b == "undefined" && typeof opt_c == "undefined") {
          diffs = /** @type {!Array.<!diff_match_patch.Diff>} */
          a;
          text1 = this.diff_text1(diffs);
        } else if (typeof a == "string" && opt_b && typeof opt_b == "object" && typeof opt_c == "undefined") {
          text1 = /** @type {string} */
          a;
          diffs = /** @type {!Array.<!diff_match_patch.Diff>} */
          opt_b;
        } else if (typeof a == "string" && typeof opt_b == "string" && opt_c && typeof opt_c == "object") {
          text1 = /** @type {string} */
          a;
          diffs = /** @type {!Array.<!diff_match_patch.Diff>} */
          opt_c;
        } else {
          throw new Error("Unknown call format to patch_make.");
        }
        if (diffs.length === 0) {
          return [];
        }
        var patches = [];
        var patch = new diff_match_patch.patch_obj();
        var patchDiffLength = 0;
        var char_count1 = 0;
        var char_count2 = 0;
        var prepatch_text = text1;
        var postpatch_text = text1;
        for (var x = 0; x < diffs.length; x++) {
          var diff_type = diffs[x][0];
          var diff_text = diffs[x][1];
          if (!patchDiffLength && diff_type !== DIFF_EQUAL) {
            patch.start1 = char_count1;
            patch.start2 = char_count2;
          }
          switch (diff_type) {
            case DIFF_INSERT:
              patch.diffs[patchDiffLength++] = diffs[x];
              patch.length2 += diff_text.length;
              postpatch_text = postpatch_text.substring(0, char_count2) + diff_text + postpatch_text.substring(char_count2);
              break;
            case DIFF_DELETE:
              patch.length1 += diff_text.length;
              patch.diffs[patchDiffLength++] = diffs[x];
              postpatch_text = postpatch_text.substring(0, char_count2) + postpatch_text.substring(char_count2 + diff_text.length);
              break;
            case DIFF_EQUAL:
              if (diff_text.length <= 2 * this.Patch_Margin && patchDiffLength && diffs.length != x + 1) {
                patch.diffs[patchDiffLength++] = diffs[x];
                patch.length1 += diff_text.length;
                patch.length2 += diff_text.length;
              } else if (diff_text.length >= 2 * this.Patch_Margin) {
                if (patchDiffLength) {
                  this.patch_addContext_(patch, prepatch_text);
                  patches.push(patch);
                  patch = new diff_match_patch.patch_obj();
                  patchDiffLength = 0;
                  prepatch_text = postpatch_text;
                  char_count1 = char_count2;
                }
              }
              break;
          }
          if (diff_type !== DIFF_INSERT) {
            char_count1 += diff_text.length;
          }
          if (diff_type !== DIFF_DELETE) {
            char_count2 += diff_text.length;
          }
        }
        if (patchDiffLength) {
          this.patch_addContext_(patch, prepatch_text);
          patches.push(patch);
        }
        return patches;
      };
      diff_match_patch.prototype.patch_deepCopy = function(patches) {
        var patchesCopy = [];
        for (var x = 0; x < patches.length; x++) {
          var patch = patches[x];
          var patchCopy = new diff_match_patch.patch_obj();
          patchCopy.diffs = [];
          for (var y = 0; y < patch.diffs.length; y++) {
            patchCopy.diffs[y] = new diff_match_patch.Diff(patch.diffs[y][0], patch.diffs[y][1]);
          }
          patchCopy.start1 = patch.start1;
          patchCopy.start2 = patch.start2;
          patchCopy.length1 = patch.length1;
          patchCopy.length2 = patch.length2;
          patchesCopy[x] = patchCopy;
        }
        return patchesCopy;
      };
      diff_match_patch.prototype.patch_apply = function(patches, text) {
        if (patches.length == 0) {
          return [text, []];
        }
        patches = this.patch_deepCopy(patches);
        var nullPadding = this.patch_addPadding(patches);
        text = nullPadding + text + nullPadding;
        this.patch_splitMax(patches);
        var delta = 0;
        var results = [];
        for (var x = 0; x < patches.length; x++) {
          var expected_loc = patches[x].start2 + delta;
          var text1 = this.diff_text1(patches[x].diffs);
          var start_loc;
          var end_loc = -1;
          if (text1.length > this.Match_MaxBits) {
            start_loc = this.match_main(
              text,
              text1.substring(0, this.Match_MaxBits),
              expected_loc
            );
            if (start_loc != -1) {
              end_loc = this.match_main(
                text,
                text1.substring(text1.length - this.Match_MaxBits),
                expected_loc + text1.length - this.Match_MaxBits
              );
              if (end_loc == -1 || start_loc >= end_loc) {
                start_loc = -1;
              }
            }
          } else {
            start_loc = this.match_main(text, text1, expected_loc);
          }
          if (start_loc == -1) {
            results[x] = false;
            delta -= patches[x].length2 - patches[x].length1;
          } else {
            results[x] = true;
            delta = start_loc - expected_loc;
            var text2;
            if (end_loc == -1) {
              text2 = text.substring(start_loc, start_loc + text1.length);
            } else {
              text2 = text.substring(start_loc, end_loc + this.Match_MaxBits);
            }
            if (text1 == text2) {
              text = text.substring(0, start_loc) + this.diff_text2(patches[x].diffs) + text.substring(start_loc + text1.length);
            } else {
              var diffs = this.diff_main(text1, text2, false);
              if (text1.length > this.Match_MaxBits && this.diff_levenshtein(diffs) / text1.length > this.Patch_DeleteThreshold) {
                results[x] = false;
              } else {
                this.diff_cleanupSemanticLossless(diffs);
                var index1 = 0;
                var index2;
                for (var y = 0; y < patches[x].diffs.length; y++) {
                  var mod = patches[x].diffs[y];
                  if (mod[0] !== DIFF_EQUAL) {
                    index2 = this.diff_xIndex(diffs, index1);
                  }
                  if (mod[0] === DIFF_INSERT) {
                    text = text.substring(0, start_loc + index2) + mod[1] + text.substring(start_loc + index2);
                  } else if (mod[0] === DIFF_DELETE) {
                    text = text.substring(0, start_loc + index2) + text.substring(start_loc + this.diff_xIndex(
                      diffs,
                      index1 + mod[1].length
                    ));
                  }
                  if (mod[0] !== DIFF_DELETE) {
                    index1 += mod[1].length;
                  }
                }
              }
            }
          }
        }
        text = text.substring(nullPadding.length, text.length - nullPadding.length);
        return [text, results];
      };
      diff_match_patch.prototype.patch_addPadding = function(patches) {
        var paddingLength = this.Patch_Margin;
        var nullPadding = "";
        for (var x = 1; x <= paddingLength; x++) {
          nullPadding += String.fromCharCode(x);
        }
        for (var x = 0; x < patches.length; x++) {
          patches[x].start1 += paddingLength;
          patches[x].start2 += paddingLength;
        }
        var patch = patches[0];
        var diffs = patch.diffs;
        if (diffs.length == 0 || diffs[0][0] != DIFF_EQUAL) {
          diffs.unshift(new diff_match_patch.Diff(DIFF_EQUAL, nullPadding));
          patch.start1 -= paddingLength;
          patch.start2 -= paddingLength;
          patch.length1 += paddingLength;
          patch.length2 += paddingLength;
        } else if (paddingLength > diffs[0][1].length) {
          var extraLength = paddingLength - diffs[0][1].length;
          diffs[0][1] = nullPadding.substring(diffs[0][1].length) + diffs[0][1];
          patch.start1 -= extraLength;
          patch.start2 -= extraLength;
          patch.length1 += extraLength;
          patch.length2 += extraLength;
        }
        patch = patches[patches.length - 1];
        diffs = patch.diffs;
        if (diffs.length == 0 || diffs[diffs.length - 1][0] != DIFF_EQUAL) {
          diffs.push(new diff_match_patch.Diff(DIFF_EQUAL, nullPadding));
          patch.length1 += paddingLength;
          patch.length2 += paddingLength;
        } else if (paddingLength > diffs[diffs.length - 1][1].length) {
          var extraLength = paddingLength - diffs[diffs.length - 1][1].length;
          diffs[diffs.length - 1][1] += nullPadding.substring(0, extraLength);
          patch.length1 += extraLength;
          patch.length2 += extraLength;
        }
        return nullPadding;
      };
      diff_match_patch.prototype.patch_splitMax = function(patches) {
        var patch_size = this.Match_MaxBits;
        for (var x = 0; x < patches.length; x++) {
          if (patches[x].length1 <= patch_size) {
            continue;
          }
          var bigpatch = patches[x];
          patches.splice(x--, 1);
          var start1 = bigpatch.start1;
          var start2 = bigpatch.start2;
          var precontext = "";
          while (bigpatch.diffs.length !== 0) {
            var patch = new diff_match_patch.patch_obj();
            var empty = true;
            patch.start1 = start1 - precontext.length;
            patch.start2 = start2 - precontext.length;
            if (precontext !== "") {
              patch.length1 = patch.length2 = precontext.length;
              patch.diffs.push(new diff_match_patch.Diff(DIFF_EQUAL, precontext));
            }
            while (bigpatch.diffs.length !== 0 && patch.length1 < patch_size - this.Patch_Margin) {
              var diff_type = bigpatch.diffs[0][0];
              var diff_text = bigpatch.diffs[0][1];
              if (diff_type === DIFF_INSERT) {
                patch.length2 += diff_text.length;
                start2 += diff_text.length;
                patch.diffs.push(bigpatch.diffs.shift());
                empty = false;
              } else if (diff_type === DIFF_DELETE && patch.diffs.length == 1 && patch.diffs[0][0] == DIFF_EQUAL && diff_text.length > 2 * patch_size) {
                patch.length1 += diff_text.length;
                start1 += diff_text.length;
                empty = false;
                patch.diffs.push(new diff_match_patch.Diff(diff_type, diff_text));
                bigpatch.diffs.shift();
              } else {
                diff_text = diff_text.substring(
                  0,
                  patch_size - patch.length1 - this.Patch_Margin
                );
                patch.length1 += diff_text.length;
                start1 += diff_text.length;
                if (diff_type === DIFF_EQUAL) {
                  patch.length2 += diff_text.length;
                  start2 += diff_text.length;
                } else {
                  empty = false;
                }
                patch.diffs.push(new diff_match_patch.Diff(diff_type, diff_text));
                if (diff_text == bigpatch.diffs[0][1]) {
                  bigpatch.diffs.shift();
                } else {
                  bigpatch.diffs[0][1] = bigpatch.diffs[0][1].substring(diff_text.length);
                }
              }
            }
            precontext = this.diff_text2(patch.diffs);
            precontext = precontext.substring(precontext.length - this.Patch_Margin);
            var postcontext = this.diff_text1(bigpatch.diffs).substring(0, this.Patch_Margin);
            if (postcontext !== "") {
              patch.length1 += postcontext.length;
              patch.length2 += postcontext.length;
              if (patch.diffs.length !== 0 && patch.diffs[patch.diffs.length - 1][0] === DIFF_EQUAL) {
                patch.diffs[patch.diffs.length - 1][1] += postcontext;
              } else {
                patch.diffs.push(new diff_match_patch.Diff(DIFF_EQUAL, postcontext));
              }
            }
            if (!empty) {
              patches.splice(++x, 0, patch);
            }
          }
        }
      };
      diff_match_patch.prototype.patch_toText = function(patches) {
        var text = [];
        for (var x = 0; x < patches.length; x++) {
          text[x] = patches[x];
        }
        return text.join("");
      };
      diff_match_patch.prototype.patch_fromText = function(textline) {
        var patches = [];
        if (!textline) {
          return patches;
        }
        var text = textline.split("\n");
        var textPointer = 0;
        var patchHeader = /^@@ -(\d+),?(\d*) \+(\d+),?(\d*) @@$/;
        while (textPointer < text.length) {
          var m = text[textPointer].match(patchHeader);
          if (!m) {
            throw new Error("Invalid patch string: " + text[textPointer]);
          }
          var patch = new diff_match_patch.patch_obj();
          patches.push(patch);
          patch.start1 = parseInt(m[1], 10);
          if (m[2] === "") {
            patch.start1--;
            patch.length1 = 1;
          } else if (m[2] == "0") {
            patch.length1 = 0;
          } else {
            patch.start1--;
            patch.length1 = parseInt(m[2], 10);
          }
          patch.start2 = parseInt(m[3], 10);
          if (m[4] === "") {
            patch.start2--;
            patch.length2 = 1;
          } else if (m[4] == "0") {
            patch.length2 = 0;
          } else {
            patch.start2--;
            patch.length2 = parseInt(m[4], 10);
          }
          textPointer++;
          while (textPointer < text.length) {
            var sign = text[textPointer].charAt(0);
            try {
              var line = decodeURI(text[textPointer].substring(1));
            } catch (ex) {
              throw new Error("Illegal escape in patch_fromText: " + line);
            }
            if (sign == "-") {
              patch.diffs.push(new diff_match_patch.Diff(DIFF_DELETE, line));
            } else if (sign == "+") {
              patch.diffs.push(new diff_match_patch.Diff(DIFF_INSERT, line));
            } else if (sign == " ") {
              patch.diffs.push(new diff_match_patch.Diff(DIFF_EQUAL, line));
            } else if (sign == "@") {
              break;
            } else if (sign === "") {
            } else {
              throw new Error('Invalid patch mode "' + sign + '" in: ' + line);
            }
            textPointer++;
          }
        }
        return patches;
      };
      diff_match_patch.patch_obj = function() {
        this.diffs = [];
        this.start1 = null;
        this.start2 = null;
        this.length1 = 0;
        this.length2 = 0;
      };
      diff_match_patch.patch_obj.prototype.toString = function() {
        var coords1, coords2;
        if (this.length1 === 0) {
          coords1 = this.start1 + ",0";
        } else if (this.length1 == 1) {
          coords1 = this.start1 + 1;
        } else {
          coords1 = this.start1 + 1 + "," + this.length1;
        }
        if (this.length2 === 0) {
          coords2 = this.start2 + ",0";
        } else if (this.length2 == 1) {
          coords2 = this.start2 + 1;
        } else {
          coords2 = this.start2 + 1 + "," + this.length2;
        }
        var text = ["@@ -" + coords1 + " +" + coords2 + " @@\n"];
        var op;
        for (var x = 0; x < this.diffs.length; x++) {
          switch (this.diffs[x][0]) {
            case DIFF_INSERT:
              op = "+";
              break;
            case DIFF_DELETE:
              op = "-";
              break;
            case DIFF_EQUAL:
              op = " ";
              break;
          }
          text[x + 1] = op + encodeURI(this.diffs[x][1]) + "\n";
        }
        return text.join("").replace(/%20/g, " ");
      };
      module.exports = diff_match_patch;
      module.exports["diff_match_patch"] = diff_match_patch;
      module.exports["DIFF_DELETE"] = DIFF_DELETE;
      module.exports["DIFF_INSERT"] = DIFF_INSERT;
      module.exports["DIFF_EQUAL"] = DIFF_EQUAL;
    }
  });

  // node_modules/dom-node-iterator/lib/adapter.js
  var require_adapter = __commonJS({
    "node_modules/dom-node-iterator/lib/adapter.js"(exports) {
      "use strict";
      exports.__esModule = true;
      function _classCallCheck(instance, Constructor) {
        if (!(instance instanceof Constructor)) {
          throw new TypeError("Cannot call a class as a function");
        }
      }
      exports["default"] = createNodeIterator;
      function createNodeIterator(root) {
        var whatToShow = arguments.length <= 1 || arguments[1] === void 0 ? 4294967295 : arguments[1];
        var filter = arguments.length <= 2 || arguments[2] === void 0 ? null : arguments[2];
        var doc = root.nodeType == 9 || root.ownerDocument;
        var iter = doc.createNodeIterator(root, whatToShow, filter, false);
        return new NodeIterator(iter, root, whatToShow, filter);
      }
      var NodeIterator = function() {
        function NodeIterator2(iter, root, whatToShow, filter) {
          _classCallCheck(this, NodeIterator2);
          this.root = root;
          this.whatToShow = whatToShow;
          this.filter = filter;
          this.referenceNode = root;
          this.pointerBeforeReferenceNode = true;
          this._iter = iter;
        }
        NodeIterator2.prototype.nextNode = function nextNode() {
          var result = this._iter.nextNode();
          this.pointerBeforeReferenceNode = false;
          if (result === null) return null;
          this.referenceNode = result;
          return this.referenceNode;
        };
        NodeIterator2.prototype.previousNode = function previousNode() {
          var result = this._iter.previousNode();
          this.pointerBeforeReferenceNode = true;
          if (result === null) return null;
          this.referenceNode = result;
          return this.referenceNode;
        };
        NodeIterator2.prototype.toString = function toString() {
          return "[object NodeIterator]";
        };
        return NodeIterator2;
      }();
    }
  });

  // node_modules/dom-node-iterator/lib/builtin.js
  var require_builtin = __commonJS({
    "node_modules/dom-node-iterator/lib/builtin.js"(exports) {
      "use strict";
      exports.__esModule = true;
      exports["default"] = createNodeIterator;
      function createNodeIterator(root) {
        var whatToShow = arguments.length <= 1 || arguments[1] === void 0 ? 4294967295 : arguments[1];
        var filter = arguments.length <= 2 || arguments[2] === void 0 ? null : arguments[2];
        var doc = root.ownerDocument;
        return doc.createNodeIterator.call(doc, root, whatToShow, filter);
      }
    }
  });

  // node_modules/dom-node-iterator/lib/implementation.js
  var require_implementation = __commonJS({
    "node_modules/dom-node-iterator/lib/implementation.js"(exports) {
      "use strict";
      exports.__esModule = true;
      function _classCallCheck(instance, Constructor) {
        if (!(instance instanceof Constructor)) {
          throw new TypeError("Cannot call a class as a function");
        }
      }
      exports["default"] = createNodeIterator;
      function createNodeIterator(root) {
        var whatToShow = arguments.length <= 1 || arguments[1] === void 0 ? 4294967295 : arguments[1];
        var filter = arguments.length <= 2 || arguments[2] === void 0 ? null : arguments[2];
        return new NodeIterator(root, whatToShow, filter);
      }
      var NodeIterator = function() {
        function NodeIterator2(root, whatToShow, filter) {
          _classCallCheck(this, NodeIterator2);
          this.root = root;
          this.whatToShow = whatToShow;
          this.filter = filter;
          this.referenceNode = root;
          this.pointerBeforeReferenceNode = true;
          this._filter = function(node) {
            return filter ? filter(node) === 1 : true;
          };
          this._show = function(node) {
            return whatToShow >> node.nodeType - 1 & true;
          };
        }
        NodeIterator2.prototype.nextNode = function nextNode() {
          var before = this.pointerBeforeReferenceNode;
          this.pointerBeforeReferenceNode = false;
          var node = this.referenceNode;
          if (before && this._show(node) && this._filter(node)) return node;
          do {
            if (node.firstChild) {
              node = node.firstChild;
              continue;
            }
            do {
              if (node === this.root) return null;
              if (node.nextSibling) break;
              node = node.parentNode;
            } while (node);
            node = node.nextSibling;
          } while (!this._show(node) || !this._filter(node));
          this.referenceNode = node;
          this.pointerBeforeReferenceNode = false;
          return node;
        };
        NodeIterator2.prototype.previousNode = function previousNode() {
          var before = this.pointerBeforeReferenceNode;
          this.pointerBeforeReferenceNode = true;
          var node = this.referenceNode;
          if (!before && this._show(node) && this._filter(node)) return node;
          do {
            if (node === this.root) return null;
            if (node.previousSibling) {
              node = node.previousSibling;
              while (node.lastChild) {
                node = node.lastChild;
              }
              continue;
            }
            node = node.parentNode;
          } while (!this._show(node) || !this._filter(node));
          this.referenceNode = node;
          this.pointerBeforeReferenceNode = true;
          return node;
        };
        NodeIterator2.prototype.toString = function toString() {
          return "[object NodeIterator]";
        };
        return NodeIterator2;
      }();
    }
  });

  // node_modules/dom-node-iterator/lib/polyfill.js
  var require_polyfill = __commonJS({
    "node_modules/dom-node-iterator/lib/polyfill.js"(exports) {
      "use strict";
      exports.__esModule = true;
      exports["default"] = getPolyfill;
      var _adapter = require_adapter();
      var _adapter2 = _interopRequireDefault(_adapter);
      var _builtin = require_builtin();
      var _builtin2 = _interopRequireDefault(_builtin);
      var _implementation = require_implementation();
      var _implementation2 = _interopRequireDefault(_implementation);
      function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : { "default": obj };
      }
      function getPolyfill() {
        try {
          var doc = typeof document === "undefined" ? {} : document;
          var iter = (0, _builtin2["default"])(doc, 4294967295, null, false);
          if (iter.referenceNode === doc) return _builtin2["default"];
          return _adapter2["default"];
        } catch (_) {
          return _implementation2["default"];
        }
      }
    }
  });

  // node_modules/dom-node-iterator/lib/shim.js
  var require_shim = __commonJS({
    "node_modules/dom-node-iterator/lib/shim.js"(exports) {
      "use strict";
      exports.__esModule = true;
      exports["default"] = shim;
      var _builtin = require_builtin();
      var _builtin2 = _interopRequireDefault(_builtin);
      var _polyfill = require_polyfill();
      var _polyfill2 = _interopRequireDefault(_polyfill);
      function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : { "default": obj };
      }
      function shim() {
        var doc = typeof document === "undefined" ? {} : document;
        var polyfill = (0, _polyfill2["default"])();
        if (polyfill !== _builtin2["default"]) doc.createNodeIterator = polyfill;
        return polyfill;
      }
    }
  });

  // node_modules/dom-node-iterator/lib/index.js
  var require_lib = __commonJS({
    "node_modules/dom-node-iterator/lib/index.js"(exports) {
      "use strict";
      exports.__esModule = true;
      var _polyfill = require_polyfill();
      var _polyfill2 = _interopRequireDefault(_polyfill);
      var _implementation = require_implementation();
      var _implementation2 = _interopRequireDefault(_implementation);
      var _shim = require_shim();
      var _shim2 = _interopRequireDefault(_shim);
      function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : { "default": obj };
      }
      var polyfill = (0, _polyfill2["default"])();
      polyfill.implementation = _implementation2["default"];
      polyfill.shim = _shim2["default"];
      exports["default"] = polyfill;
    }
  });

  // node_modules/dom-node-iterator/polyfill.js
  var require_polyfill2 = __commonJS({
    "node_modules/dom-node-iterator/polyfill.js"(exports, module) {
      module.exports = require_polyfill()["default"];
    }
  });

  // node_modules/dom-node-iterator/implementation.js
  var require_implementation2 = __commonJS({
    "node_modules/dom-node-iterator/implementation.js"(exports, module) {
      module.exports = require_implementation()["default"];
    }
  });

  // node_modules/dom-node-iterator/shim.js
  var require_shim2 = __commonJS({
    "node_modules/dom-node-iterator/shim.js"(exports, module) {
      module.exports = require_shim()["default"];
    }
  });

  // node_modules/dom-node-iterator/index.js
  var require_dom_node_iterator = __commonJS({
    "node_modules/dom-node-iterator/index.js"(exports, module) {
      module.exports = require_lib()["default"];
      module.exports.getPolyfill = require_polyfill2();
      module.exports.implementation = require_implementation2();
      module.exports.shim = require_shim2();
    }
  });

  // node_modules/ancestors/index.js
  var require_ancestors = __commonJS({
    "node_modules/ancestors/index.js"(exports, module) {
      module.exports = parents;
      function parents(node, filter) {
        var out = [];
        filter = filter || noop;
        do {
          out.push(node);
          node = node.parentNode;
        } while (node && node.tagName && filter(node));
        return out.slice(1);
      }
      function noop(n) {
        return true;
      }
    }
  });

  // node_modules/index-of/index.js
  var require_index_of = __commonJS({
    "node_modules/index-of/index.js"(exports, module) {
      "use strict";
      module.exports = function indexOf(arr, ele, start) {
        start = start || 0;
        var idx = -1;
        if (arr == null) return idx;
        var len = arr.length;
        var i = start < 0 ? len + start : start;
        if (i >= arr.length) {
          return -1;
        }
        while (i < len) {
          if (arr[i] === ele) {
            return i;
          }
          i++;
        }
        return -1;
      };
    }
  });

  // node_modules/dom-anchor-text-quote/node_modules/dom-seek/lib/index.js
  var require_lib2 = __commonJS({
    "node_modules/dom-anchor-text-quote/node_modules/dom-seek/lib/index.js"(exports) {
      "use strict";
      exports.__esModule = true;
      exports["default"] = seek;
      var _ancestors = require_ancestors();
      var _ancestors2 = _interopRequireDefault(_ancestors);
      var _indexOf = require_index_of();
      var _indexOf2 = _interopRequireDefault(_indexOf);
      function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : { "default": obj };
      }
      var E_SHOW = "Argument 1 of seek must use filter NodeFilter.SHOW_TEXT.";
      var E_WHERE = "Argument 2 of seek must be a number or a Text Node.";
      var SHOW_TEXT = 4;
      var TEXT_NODE = 3;
      function seek(iter, where) {
        if (iter.whatToShow !== SHOW_TEXT) {
          throw new Error(E_SHOW);
        }
        var count = 0;
        var node = iter.referenceNode;
        var predicates = null;
        if (isNumber(where)) {
          predicates = {
            forward: function forward2() {
              return count < where;
            },
            backward: function backward2() {
              return count > where;
            }
          };
        } else if (isText(where)) {
          var forward = before(node, where) ? function() {
            return false;
          } : function() {
            return node !== where;
          };
          var backward = function backward2() {
            return node != where || !iter.pointerBeforeReferenceNode;
          };
          predicates = { forward, backward };
        } else {
          throw new Error(E_WHERE);
        }
        while (predicates.forward() && (node = iter.nextNode()) !== null) {
          count += node.nodeValue.length;
        }
        while (predicates.backward() && (node = iter.previousNode()) !== null) {
          count -= node.nodeValue.length;
        }
        return count;
      }
      function isNumber(n) {
        return !isNaN(parseInt(n)) && isFinite(n);
      }
      function isText(node) {
        return node.nodeType === TEXT_NODE;
      }
      function before(ref, node) {
        if (ref === node) return false;
        var common = null;
        var left = [ref].concat((0, _ancestors2["default"])(ref)).reverse();
        var right = [node].concat((0, _ancestors2["default"])(node)).reverse();
        while (left[0] === right[0]) {
          common = left.shift();
          right.shift();
        }
        left = left[0];
        right = right[0];
        var l = (0, _indexOf2["default"])(common.childNodes, left);
        var r = (0, _indexOf2["default"])(common.childNodes, right);
        return l > r;
      }
    }
  });

  // node_modules/dom-anchor-text-quote/node_modules/dom-seek/index.js
  var require_dom_seek = __commonJS({
    "node_modules/dom-anchor-text-quote/node_modules/dom-seek/index.js"(exports, module) {
      module.exports = require_lib2()["default"];
    }
  });

  // node_modules/dom-anchor-text-quote/node_modules/dom-anchor-text-position/lib/range-to-string.js
  var require_range_to_string = __commonJS({
    "node_modules/dom-anchor-text-quote/node_modules/dom-anchor-text-position/lib/range-to-string.js"(exports) {
      "use strict";
      Object.defineProperty(exports, "__esModule", {
        value: true
      });
      exports.default = rangeToString;
      function nextNode(node, skipChildren) {
        if (!skipChildren && node.firstChild) {
          return node.firstChild;
        }
        do {
          if (node.nextSibling) {
            return node.nextSibling;
          }
          node = node.parentNode;
        } while (node);
        return node;
      }
      function firstNode(range) {
        if (range.startContainer.nodeType === Node.ELEMENT_NODE) {
          var node = range.startContainer.childNodes[range.startOffset];
          return node || nextNode(
            range.startContainer,
            true
            /* skip children */
          );
        }
        return range.startContainer;
      }
      function firstNodeAfter(range) {
        if (range.endContainer.nodeType === Node.ELEMENT_NODE) {
          var node = range.endContainer.childNodes[range.endOffset];
          return node || nextNode(
            range.endContainer,
            true
            /* skip children */
          );
        }
        return nextNode(range.endContainer);
      }
      function forEachNodeInRange(range, cb) {
        var node = firstNode(range);
        var pastEnd = firstNodeAfter(range);
        while (node !== pastEnd) {
          cb(node);
          node = nextNode(node);
        }
      }
      function rangeToString(range) {
        var text = "";
        forEachNodeInRange(range, function(node) {
          if (node.nodeType !== Node.TEXT_NODE) {
            return;
          }
          var start = node === range.startContainer ? range.startOffset : 0;
          var end = node === range.endContainer ? range.endOffset : node.textContent.length;
          text += node.textContent.slice(start, end);
        });
        return text;
      }
    }
  });

  // node_modules/dom-anchor-text-quote/node_modules/dom-anchor-text-position/lib/index.js
  var require_lib3 = __commonJS({
    "node_modules/dom-anchor-text-quote/node_modules/dom-anchor-text-position/lib/index.js"(exports) {
      "use strict";
      Object.defineProperty(exports, "__esModule", {
        value: true
      });
      exports.fromRange = fromRange;
      exports.toRange = toRange;
      var _domNodeIterator = require_dom_node_iterator();
      var _domNodeIterator2 = _interopRequireDefault(_domNodeIterator);
      var _domSeek = require_dom_seek();
      var _domSeek2 = _interopRequireDefault(_domSeek);
      var _rangeToString = require_range_to_string();
      var _rangeToString2 = _interopRequireDefault(_rangeToString);
      function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : { default: obj };
      }
      var SHOW_TEXT = 4;
      function fromRange(root, range) {
        if (root === void 0) {
          throw new Error('missing required parameter "root"');
        }
        if (range === void 0) {
          throw new Error('missing required parameter "range"');
        }
        var document2 = root.ownerDocument;
        var prefix = document2.createRange();
        var startNode = range.startContainer;
        var startOffset = range.startOffset;
        prefix.setStart(root, 0);
        prefix.setEnd(startNode, startOffset);
        var start = (0, _rangeToString2.default)(prefix).length;
        var end = start + (0, _rangeToString2.default)(range).length;
        return {
          start,
          end
        };
      }
      function toRange(root) {
        var selector = arguments.length <= 1 || arguments[1] === void 0 ? {} : arguments[1];
        if (root === void 0) {
          throw new Error('missing required parameter "root"');
        }
        var document2 = root.ownerDocument;
        var range = document2.createRange();
        var iter = (0, _domNodeIterator2.default)(root, SHOW_TEXT);
        var start = selector.start || 0;
        var end = selector.end || start;
        var count = (0, _domSeek2.default)(iter, start);
        var remainder = start - count;
        if (iter.pointerBeforeReferenceNode) {
          range.setStart(iter.referenceNode, remainder);
        } else {
          range.setStart(iter.nextNode(), remainder);
          iter.previousNode();
        }
        var length = end - start + remainder;
        count = (0, _domSeek2.default)(iter, length);
        remainder = length - count;
        if (iter.pointerBeforeReferenceNode) {
          range.setEnd(iter.referenceNode, remainder);
        } else {
          range.setEnd(iter.nextNode(), remainder);
        }
        return range;
      }
    }
  });

  // node_modules/dom-anchor-text-quote/node_modules/dom-anchor-text-position/index.js
  var require_dom_anchor_text_position = __commonJS({
    "node_modules/dom-anchor-text-quote/node_modules/dom-anchor-text-position/index.js"(exports, module) {
      module.exports = require_lib3();
    }
  });

  // node_modules/dom-anchor-text-quote/lib/index.js
  var require_lib4 = __commonJS({
    "node_modules/dom-anchor-text-quote/lib/index.js"(exports) {
      "use strict";
      Object.defineProperty(exports, "__esModule", {
        value: true
      });
      exports.fromRange = fromRange;
      exports.fromTextPosition = fromTextPosition;
      exports.toRange = toRange;
      exports.toTextPosition = toTextPosition;
      var _diffMatchPatch = require_diff_match_patch();
      var _diffMatchPatch2 = _interopRequireDefault(_diffMatchPatch);
      var _domAnchorTextPosition = require_dom_anchor_text_position();
      var textPosition = _interopRequireWildcard(_domAnchorTextPosition);
      function _interopRequireWildcard(obj) {
        if (obj && obj.__esModule) {
          return obj;
        } else {
          var newObj = {};
          if (obj != null) {
            for (var key in obj) {
              if (Object.prototype.hasOwnProperty.call(obj, key)) newObj[key] = obj[key];
            }
          }
          newObj.default = obj;
          return newObj;
        }
      }
      function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : { default: obj };
      }
      var SLICE_LENGTH = 32;
      var SLICE_RE = new RegExp("(.|[\r\n]){1," + String(SLICE_LENGTH) + "}", "g");
      var CONTEXT_LENGTH = SLICE_LENGTH;
      function fromRange(root, range) {
        if (root === void 0) {
          throw new Error('missing required parameter "root"');
        }
        if (range === void 0) {
          throw new Error('missing required parameter "range"');
        }
        var position = textPosition.fromRange(root, range);
        return fromTextPosition(root, position);
      }
      function fromTextPosition(root, selector) {
        if (root === void 0) {
          throw new Error('missing required parameter "root"');
        }
        if (selector === void 0) {
          throw new Error('missing required parameter "selector"');
        }
        var start = selector.start;
        if (start === void 0) {
          throw new Error('selector missing required property "start"');
        }
        if (start < 0) {
          throw new Error('property "start" must be a non-negative integer');
        }
        var end = selector.end;
        if (end === void 0) {
          throw new Error('selector missing required property "end"');
        }
        if (end < 0) {
          throw new Error('property "end" must be a non-negative integer');
        }
        var exact = root.textContent.substr(start, end - start);
        var prefixStart = Math.max(0, start - CONTEXT_LENGTH);
        var prefix = root.textContent.substr(prefixStart, start - prefixStart);
        var suffixEnd = Math.min(root.textContent.length, end + CONTEXT_LENGTH);
        var suffix = root.textContent.substr(end, suffixEnd - end);
        return { exact, prefix, suffix };
      }
      function toRange(root, selector) {
        var options = arguments.length > 2 && arguments[2] !== void 0 ? arguments[2] : {};
        var position = toTextPosition(root, selector, options);
        if (position === null) {
          return null;
        } else {
          return textPosition.toRange(root, position);
        }
      }
      function toTextPosition(root, selector) {
        var options = arguments.length > 2 && arguments[2] !== void 0 ? arguments[2] : {};
        if (root === void 0) {
          throw new Error('missing required parameter "root"');
        }
        if (selector === void 0) {
          throw new Error('missing required parameter "selector"');
        }
        var exact = selector.exact;
        if (exact === void 0) {
          throw new Error('selector missing required property "exact"');
        }
        var prefix = selector.prefix, suffix = selector.suffix;
        var hint = options.hint;
        var dmp = new _diffMatchPatch2.default();
        dmp.Match_Distance = root.textContent.length * 2;
        var slices = exact.match(SLICE_RE);
        var loc = hint === void 0 ? root.textContent.length / 2 | 0 : hint;
        var start = Number.POSITIVE_INFINITY;
        var end = Number.NEGATIVE_INFINITY;
        var result = -1;
        var havePrefix = prefix !== void 0;
        var haveSuffix = suffix !== void 0;
        var foundPrefix = false;
        if (havePrefix) {
          result = dmp.match_main(root.textContent, prefix, loc);
          if (result > -1) {
            loc = result + prefix.length;
            foundPrefix = true;
          }
        }
        if (haveSuffix && !foundPrefix) {
          result = dmp.match_main(root.textContent, suffix, loc + exact.length);
          if (result > -1) {
            loc = result - exact.length;
          }
        }
        var firstSlice = slices.shift();
        result = dmp.match_main(root.textContent, firstSlice, loc);
        if (result > -1) {
          start = result;
          loc = end = start + firstSlice.length;
        } else {
          return null;
        }
        var foldSlices = function foldSlices2(acc2, slice) {
          if (!acc2) {
            return null;
          }
          var result2 = dmp.match_main(root.textContent, slice, acc2.loc);
          if (result2 === -1) {
            return null;
          }
          acc2.loc = result2 + slice.length;
          acc2.start = Math.min(acc2.start, result2);
          acc2.end = Math.max(acc2.end, result2 + slice.length);
          return acc2;
        };
        dmp.Match_Distance = 64;
        var acc = slices.reduce(foldSlices, { start, end, loc });
        if (!acc) {
          return null;
        }
        return { start: acc.start, end: acc.end };
      }
    }
  });

  // node_modules/dom-anchor-text-quote/index.js
  var require_dom_anchor_text_quote = __commonJS({
    "node_modules/dom-anchor-text-quote/index.js"(exports, module) {
      module.exports = require_lib4();
    }
  });

  // node_modules/dom-seek/lib/index.js
  var require_lib5 = __commonJS({
    "node_modules/dom-seek/lib/index.js"(exports) {
      "use strict";
      Object.defineProperty(exports, "__esModule", {
        value: true
      });
      exports["default"] = seek;
      var E_END = "Iterator exhausted before seek ended.";
      var E_SHOW = "Argument 1 of seek must use filter NodeFilter.SHOW_TEXT.";
      var E_WHERE = "Argument 2 of seek must be an integer or a Text Node.";
      var DOCUMENT_POSITION_PRECEDING = 2;
      var SHOW_TEXT = 4;
      var TEXT_NODE = 3;
      function seek(iter, where) {
        if (iter.whatToShow !== SHOW_TEXT) {
          var error;
          try {
            error = new DOMException(E_SHOW, "InvalidStateError");
          } catch (_unused) {
            error = new Error(E_SHOW);
            error.code = 11;
            error.name = "InvalidStateError";
            error.toString = function() {
              return "InvalidStateError: ".concat(E_SHOW);
            };
          }
          throw error;
        }
        var count = 0;
        var node = iter.referenceNode;
        var predicates = null;
        if (isInteger(where)) {
          predicates = {
            forward: function forward2() {
              return count < where;
            },
            backward: function backward2() {
              return count > where || !iter.pointerBeforeReferenceNode;
            }
          };
        } else if (isText(where)) {
          var forward = before(node, where) ? function() {
            return false;
          } : function() {
            return node !== where;
          };
          var backward = function backward2() {
            return node !== where || !iter.pointerBeforeReferenceNode;
          };
          predicates = {
            forward,
            backward
          };
        } else {
          throw new TypeError(E_WHERE);
        }
        while (predicates.forward()) {
          node = iter.nextNode();
          if (node === null) {
            throw new RangeError(E_END);
          }
          count += node.nodeValue.length;
        }
        if (iter.nextNode()) {
          node = iter.previousNode();
        }
        while (predicates.backward()) {
          node = iter.previousNode();
          if (node === null) {
            throw new RangeError(E_END);
          }
          count -= node.nodeValue.length;
        }
        if (!isText(iter.referenceNode)) {
          throw new RangeError(E_END);
        }
        return count;
      }
      function isInteger(n) {
        if (typeof n !== "number") return false;
        return isFinite(n) && Math.floor(n) === n;
      }
      function isText(node) {
        return node.nodeType === TEXT_NODE;
      }
      function before(ref, node) {
        return ref.compareDocumentPosition(node) & DOCUMENT_POSITION_PRECEDING;
      }
    }
  });

  // node_modules/dom-seek/index.js
  var require_dom_seek2 = __commonJS({
    "node_modules/dom-seek/index.js"(exports, module) {
      module.exports = require_lib5()["default"];
    }
  });

  // node_modules/dom-anchor-text-position/lib/range-to-string.js
  var require_range_to_string2 = __commonJS({
    "node_modules/dom-anchor-text-position/lib/range-to-string.js"(exports) {
      "use strict";
      Object.defineProperty(exports, "__esModule", {
        value: true
      });
      exports["default"] = rangeToString;
      function nextNode(node, skipChildren) {
        if (!skipChildren && node.firstChild) {
          return node.firstChild;
        }
        do {
          if (node.nextSibling) {
            return node.nextSibling;
          }
          node = node.parentNode;
        } while (node);
        return node;
      }
      function firstNode(range) {
        if (range.startContainer.nodeType === Node.ELEMENT_NODE) {
          var node = range.startContainer.childNodes[range.startOffset];
          return node || nextNode(
            range.startContainer,
            true
            /* skip children */
          );
        }
        return range.startContainer;
      }
      function firstNodeAfter(range) {
        if (range.endContainer.nodeType === Node.ELEMENT_NODE) {
          var node = range.endContainer.childNodes[range.endOffset];
          return node || nextNode(
            range.endContainer,
            true
            /* skip children */
          );
        }
        return nextNode(range.endContainer);
      }
      function forEachNodeInRange(range, cb) {
        var node = firstNode(range);
        var pastEnd = firstNodeAfter(range);
        while (node !== pastEnd) {
          cb(node);
          node = nextNode(node);
        }
      }
      function rangeToString(range) {
        var text = "";
        forEachNodeInRange(range, function(node) {
          if (node.nodeType !== Node.TEXT_NODE) {
            return;
          }
          var start = node === range.startContainer ? range.startOffset : 0;
          var end = node === range.endContainer ? range.endOffset : node.textContent.length;
          text += node.textContent.slice(start, end);
        });
        return text;
      }
    }
  });

  // node_modules/dom-anchor-text-position/lib/index.js
  var require_lib6 = __commonJS({
    "node_modules/dom-anchor-text-position/lib/index.js"(exports) {
      "use strict";
      Object.defineProperty(exports, "__esModule", {
        value: true
      });
      exports.fromRange = fromRange;
      exports.toRange = toRange;
      var _domSeek = _interopRequireDefault(require_dom_seek2());
      var _rangeToString = _interopRequireDefault(require_range_to_string2());
      function _interopRequireDefault(obj) {
        return obj && obj.__esModule ? obj : { "default": obj };
      }
      var SHOW_TEXT = 4;
      function fromRange(root, range) {
        if (root === void 0) {
          throw new Error('missing required parameter "root"');
        }
        if (range === void 0) {
          throw new Error('missing required parameter "range"');
        }
        var document2 = root.ownerDocument;
        var prefix = document2.createRange();
        var startNode = range.startContainer;
        var startOffset = range.startOffset;
        prefix.setStart(root, 0);
        prefix.setEnd(startNode, startOffset);
        var start = (0, _rangeToString["default"])(prefix).length;
        var end = start + (0, _rangeToString["default"])(range).length;
        return {
          start,
          end
        };
      }
      function toRange(root) {
        var selector = arguments.length > 1 && arguments[1] !== void 0 ? arguments[1] : {};
        if (root === void 0) {
          throw new Error('missing required parameter "root"');
        }
        var document2 = root.ownerDocument;
        var range = document2.createRange();
        var iter = document2.createNodeIterator(root, SHOW_TEXT);
        var start = selector.start || 0;
        var end = selector.end || start;
        var startOffset = start - (0, _domSeek["default"])(iter, start);
        var startNode = iter.referenceNode;
        var remainder = end - start + startOffset;
        var endOffset = remainder - (0, _domSeek["default"])(iter, remainder);
        var endNode = iter.referenceNode;
        range.setStart(startNode, startOffset);
        range.setEnd(endNode, endOffset);
        return range;
      }
    }
  });

  // node_modules/dom-anchor-text-position/index.js
  var require_dom_anchor_text_position2 = __commonJS({
    "node_modules/dom-anchor-text-position/index.js"(exports, module) {
      module.exports = require_lib6();
    }
  });

  // extension/content/annotate.src.js
  var import_dom_anchor_text_quote = __toESM(require_dom_anchor_text_quote(), 1);
  var import_dom_anchor_text_position = __toESM(require_dom_anchor_text_position2(), 1);

  // extension/content/buildMarkdown.js
  function buildMarkdown({ pageTitle, pageUrl, annotations: annotations2 }) {
    const label = (pageTitle || pageUrl || "").trim() || pageUrl || "";
    const lines = ["## Annotations", "", `**Source:** [${label}](${pageUrl})`, ""];
    const items = Array.isArray(annotations2) ? annotations2 : [];
    for (let i = 0; i < items.length; i++) {
      const a = items[i];
      const quote = String(a?.quote ?? "");
      const quoteLines = quote.split("\n").map((l) => `> ${l}`).join("\n");
      lines.push(quoteLines);
      if (a?.textFragmentUrl) {
        lines.push("");
        lines.push(`[citer](${a.textFragmentUrl})`);
      }
      if (i < items.length - 1) {
        lines.push("");
        lines.push("---");
        lines.push("");
      }
    }
    return lines.join("\n");
  }

  // extension/content/annotate.src.js
  var STORAGE_PREFIX = "kb_anno:";
  var HOST_ID = "kb-annotate-root";
  var PAGE_STYLE_ID = "kb-annotate-page-style";
  var HL_CLASS = "kb-hl";
  var Z = 2147483647;
  var SHADOW_CSS = `
  :host { all: initial; }
  * { box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
  button { font: inherit; cursor: pointer; }

  .badge {
    position: fixed; top: 16px; right: 16px; z-index: ${Z};
    display: none; align-items: center; gap: 6px;
    background: #ffffff; color: #1f2328;
    border: 1px solid #d0d7de; border-radius: 999px;
    padding: 4px 10px; font-size: 12px; font-weight: 600;
    box-shadow: 0 2px 6px rgba(0,0,0,0.12);
    user-select: none;
  }
  .badge.on { display: inline-flex; }
  .badge:hover { background: #f6f8fa; }
  .badge-dot {
    width: 8px; height: 8px; border-radius: 50%; background: #0969da;
  }

  .adder {
    position: fixed; z-index: ${Z};
    display: none; gap: 4px;
    background: #1f2328; color: #ffffff;
    border-radius: 6px; padding: 4px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.25);
  }
  .adder.on { display: inline-flex; }
  .adder-btn {
    background: transparent; color: inherit; border: 0;
    padding: 4px 10px; border-radius: 4px; font-size: 12px;
  }
  .adder-btn:hover { background: rgba(255,255,255,0.12); }
  .adder-btn.dismiss { padding: 4px 8px; color: rgba(255,255,255,0.55); }

  .drawer {
    position: fixed; top: 0; right: 0; height: 100vh; width: 320px;
    z-index: ${Z};
    background: #ffffff; color: #1f2328;
    border-left: 1px solid #d0d7de;
    box-shadow: -4px 0 16px rgba(0,0,0,0.10);
    transform: translateX(100%); transition: transform 180ms ease-out;
    display: flex; flex-direction: column;
  }
  .drawer.open { transform: translateX(0); }
  @media (prefers-reduced-motion: reduce) {
    .drawer { transition: none; }
  }
  .drawer-header { padding: 12px 16px; border-bottom: 1px solid #d0d7de; }
  .drawer-title { font-size: 13px; font-weight: 600; margin-bottom: 2px; word-break: break-word; }
  .drawer-url { font-size: 11px; color: #57606a; word-break: break-all; }
  .drawer-count { font-size: 11px; color: #57606a; margin-top: 4px; }
  .drawer-close {
    position: absolute; top: 8px; right: 8px;
    background: transparent; border: 0; color: #57606a;
    width: 24px; height: 24px; border-radius: 50%; font-size: 14px;
  }
  .drawer-close:hover { background: #f6f8fa; }
  .drawer-list { flex: 1; overflow-y: auto; padding: 8px 0; }
  .drawer-empty { padding: 16px; color: #57606a; font-size: 12px; text-align: center; }
  .drawer-item {
    padding: 8px 16px; border-bottom: 1px solid #f0f2f5;
    display: flex; gap: 8px; align-items: flex-start;
  }
  .drawer-item:hover { background: #f6f8fa; }
  .drawer-quote {
    flex: 1; font-size: 12px; line-height: 1.4;
    border-left: 3px solid rgba(9,105,218,0.4); padding-left: 8px;
    color: #1f2328;
    display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .drawer-del {
    background: transparent; border: 0; color: #cf222e; font-size: 13px;
    padding: 2px 6px; border-radius: 4px; opacity: 0.6;
  }
  .drawer-del:hover { background: rgba(207,34,46,0.10); opacity: 1; }
  .drawer-footer { padding: 12px 16px; border-top: 1px solid #d0d7de; }
  .drawer-push {
    width: 100%; background: #0969da; color: #ffffff; border: 0;
    padding: 8px 12px; border-radius: 6px; font-size: 13px; font-weight: 600;
  }
  .drawer-push:hover:not(:disabled) { background: #0860c4; }
  .drawer-push:disabled { background: #adbac7; cursor: not-allowed; }
  .drawer-status { font-size: 11px; color: #57606a; margin-top: 6px; min-height: 14px; }
  .drawer-status.success { color: #1a7f37; }
  .drawer-status.error { color: #cf222e; }
`;
  var PAGE_CSS = `
  .${HL_CLASS} {
    background-color: rgba(9, 105, 218, 0.22);
    mix-blend-mode: multiply;
    border-radius: 2px;
    box-shadow: 0 1px 0 rgba(9, 105, 218, 0.35);
    cursor: pointer;
  }
`;
  var mode = false;
  var annotations = [];
  var host = null;
  var shadow = null;
  var badgeEl = null;
  var adderEl = null;
  var drawerEl = null;
  var drawerStatusEl = null;
  var drawerPushBtn = null;
  var nextId = 1;
  var currentRange = null;
  var selectionDebounce = null;
  var lastUrl = "";
  function stripTrackingParams(u) {
    try {
      const url = new URL(u);
      const drop = [];
      url.searchParams.forEach((_, k) => {
        if (k.startsWith("utm_") || k.startsWith("mc_") || k === "fbclid" || k === "gclid" || k === "yclid") {
          drop.push(k);
        }
      });
      for (const k of drop) url.searchParams.delete(k);
      return url.toString();
    } catch {
      return u;
    }
  }
  function canonicalUrl() {
    const link = document.querySelector('link[rel="canonical"]');
    if (link?.href) return stripTrackingParams(link.href);
    return stripTrackingParams(location.origin + location.pathname + location.search);
  }
  function storageKey() {
    return STORAGE_PREFIX + canonicalUrl();
  }
  function textFragmentUrl(quote) {
    const exact = String(quote?.exact ?? "").slice(0, 200);
    if (!exact) return null;
    return canonicalUrl() + "#:~:text=" + encodeURIComponent(exact);
  }
  async function loadAnnotations() {
    const key = storageKey();
    const data = await chrome.storage.local.get(key);
    annotations = Array.isArray(data[key]) ? data[key] : [];
    for (const a of annotations) if (a.id >= nextId) nextId = a.id + 1;
  }
  async function saveAnnotations() {
    const key = storageKey();
    await chrome.storage.local.set({ [key]: annotations });
  }
  function ensureHost() {
    if (host) return;
    host = document.createElement("div");
    host.id = HOST_ID;
    host.style.cssText = `all: initial; position: static; z-index: ${Z};`;
    document.documentElement.appendChild(host);
    shadow = host.attachShadow({ mode: "open" });
    const style = document.createElement("style");
    style.textContent = SHADOW_CSS;
    shadow.appendChild(style);
    if (!document.getElementById(PAGE_STYLE_ID)) {
      const pageStyle = document.createElement("style");
      pageStyle.id = PAGE_STYLE_ID;
      pageStyle.textContent = PAGE_CSS;
      (document.head || document.documentElement).appendChild(pageStyle);
    }
  }
  function wrapRange(range, dataId) {
    const ancestor = range.commonAncestorContainer;
    const root = ancestor.nodeType === Node.ELEMENT_NODE ? ancestor : ancestor.parentNode;
    if (!root) return;
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const inRange = [];
    while (walker.nextNode()) {
      const n = (
        /** @type {Text} */
        walker.currentNode
      );
      if (range.intersectsNode(n)) inRange.push(n);
    }
    for (let n of inRange) {
      let startOffset = 0;
      let endOffset = n.length;
      if (n === range.startContainer) startOffset = range.startOffset;
      if (n === range.endContainer) endOffset = range.endOffset;
      if (startOffset >= endOffset) continue;
      let target = n;
      if (startOffset > 0) {
        target = n.splitText(startOffset);
        endOffset -= startOffset;
      }
      if (endOffset < target.length) {
        target.splitText(endOffset);
      }
      if (host && host.contains(target)) continue;
      if (target.parentElement?.classList.contains(HL_CLASS)) continue;
      const span = document.createElement("span");
      span.className = HL_CLASS;
      span.dataset.kbId = String(dataId);
      const parent = target.parentNode;
      if (!parent) continue;
      parent.insertBefore(span, target);
      span.appendChild(target);
    }
  }
  function unwrapHighlight(id) {
    const spans = document.querySelectorAll(`.${HL_CLASS}[data-kb-id="${id}"]`);
    for (const s of spans) {
      const parent = s.parentNode;
      if (!parent) continue;
      while (s.firstChild) parent.insertBefore(s.firstChild, s);
      parent.removeChild(s);
    }
  }
  function unwrapAllHighlights() {
    for (const s of document.querySelectorAll(`.${HL_CLASS}`)) {
      const parent = s.parentNode;
      if (!parent) continue;
      while (s.firstChild) parent.insertBefore(s.firstChild, s);
      parent.removeChild(s);
    }
  }
  function reapplyAll() {
    for (const ann of annotations) {
      try {
        let range = (0, import_dom_anchor_text_quote.toRange)(document.body, ann.quote, { hint: ann.position?.start ?? 0 });
        if (!range && ann.position) range = (0, import_dom_anchor_text_position.toRange)(document.body, ann.position);
        if (range) wrapRange(range, ann.id);
      } catch {
      }
    }
  }
  function buildAdder() {
    adderEl = document.createElement("div");
    adderEl.className = "adder";
    const hl = document.createElement("button");
    hl.className = "adder-btn";
    hl.type = "button";
    hl.textContent = "\u{1F58D} Surligner";
    hl.addEventListener("mousedown", (e) => e.preventDefault());
    hl.addEventListener("click", () => {
      if (currentRange) addHighlightFromRange(currentRange);
      hideAdder();
    });
    const close = document.createElement("button");
    close.className = "adder-btn dismiss";
    close.type = "button";
    close.textContent = "\u2715";
    close.addEventListener("mousedown", (e) => e.preventDefault());
    close.addEventListener("click", hideAdder);
    adderEl.appendChild(hl);
    adderEl.appendChild(close);
    shadow.appendChild(adderEl);
  }
  function showAdder(range) {
    if (!adderEl) buildAdder();
    const rect = range.getBoundingClientRect();
    if (!rect.width && !rect.height) return;
    const W = 180;
    const H = 32;
    let x = rect.right + 4;
    let y = rect.bottom + 4;
    if (x + W > window.innerWidth - 8) x = Math.max(8, window.innerWidth - W - 8);
    if (y + H > window.innerHeight - 8) y = Math.max(8, rect.top - H - 4);
    adderEl.style.left = `${x}px`;
    adderEl.style.top = `${y}px`;
    adderEl.classList.add("on");
  }
  function hideAdder() {
    adderEl?.classList.remove("on");
  }
  function onSelectionChange() {
    if (!mode) return;
    clearTimeout(selectionDebounce);
    selectionDebounce = setTimeout(() => {
      const sel = window.getSelection();
      if (!sel || sel.isCollapsed || sel.toString().trim().length < 2) {
        hideAdder();
        return;
      }
      const range = sel.getRangeAt(0);
      const node = range.commonAncestorContainer;
      if (host?.contains(node)) return;
      const editable = (node.nodeType === Node.ELEMENT_NODE ? node : node.parentElement)?.closest?.(
        'input[type="password"], [contenteditable]'
      );
      if (editable) return;
      currentRange = range.cloneRange();
      showAdder(range);
    }, 200);
  }
  function addHighlightFromRange(range) {
    let quote;
    let position;
    try {
      quote = (0, import_dom_anchor_text_quote.fromRange)(document.body, range);
      position = (0, import_dom_anchor_text_position.fromRange)(document.body, range);
    } catch {
      return;
    }
    if (!quote?.exact) return;
    const ann = {
      id: nextId++,
      quote,
      position,
      createdAt: (/* @__PURE__ */ new Date()).toISOString()
    };
    annotations.push(ann);
    wrapRange(range, ann.id);
    saveAnnotations();
    renderBadge();
    if (drawerEl?.classList.contains("open")) renderDrawer();
    window.getSelection()?.removeAllRanges();
  }
  function buildBadge() {
    badgeEl = document.createElement("div");
    badgeEl.className = "badge";
    badgeEl.title = "Annotations kenboard \u2014 clic pour ouvrir le panneau";
    const dot = document.createElement("span");
    dot.className = "badge-dot";
    const txt = document.createElement("span");
    txt.className = "badge-text";
    badgeEl.appendChild(dot);
    badgeEl.appendChild(txt);
    badgeEl.addEventListener("click", openDrawer);
    shadow.appendChild(badgeEl);
  }
  function renderBadge() {
    if (!badgeEl) buildBadge();
    badgeEl.querySelector(".badge-text").textContent = `kb \xB7 ${annotations.length}`;
    badgeEl.classList.toggle("on", mode);
  }
  function buildDrawer() {
    drawerEl = document.createElement("div");
    drawerEl.className = "drawer";
    shadow.appendChild(drawerEl);
  }
  function openDrawer() {
    if (!drawerEl) buildDrawer();
    renderDrawer();
    drawerEl.classList.add("open");
  }
  function closeDrawer() {
    drawerEl?.classList.remove("open");
  }
  function renderDrawer() {
    if (!drawerEl) return;
    drawerEl.replaceChildren();
    const header = document.createElement("div");
    header.className = "drawer-header";
    const close = document.createElement("button");
    close.className = "drawer-close";
    close.type = "button";
    close.textContent = "\u2715";
    close.title = "Fermer";
    close.addEventListener("click", closeDrawer);
    const title = document.createElement("div");
    title.className = "drawer-title";
    title.textContent = document.title || canonicalUrl();
    const url = document.createElement("div");
    url.className = "drawer-url";
    url.textContent = canonicalUrl();
    const count = document.createElement("div");
    count.className = "drawer-count";
    count.textContent = `${annotations.length} annotation${annotations.length === 1 ? "" : "s"}`;
    header.appendChild(close);
    header.appendChild(title);
    header.appendChild(url);
    header.appendChild(count);
    drawerEl.appendChild(header);
    const list = document.createElement("div");
    list.className = "drawer-list";
    if (annotations.length === 0) {
      const empty = document.createElement("div");
      empty.className = "drawer-empty";
      empty.textContent = "Aucune annotation. S\xE9lectionnez du texte sur la page puis cliquez \xAB \u{1F58D} Surligner \xBB.";
      list.appendChild(empty);
    } else {
      for (const ann of annotations) {
        const item = document.createElement("div");
        item.className = "drawer-item";
        const q = document.createElement("div");
        q.className = "drawer-quote";
        q.textContent = String(ann.quote?.exact ?? "");
        const del = document.createElement("button");
        del.className = "drawer-del";
        del.type = "button";
        del.title = "Supprimer cette annotation";
        del.textContent = "\u{1F5D1}";
        del.addEventListener("click", () => {
          annotations = annotations.filter((a) => a.id !== ann.id);
          unwrapHighlight(ann.id);
          saveAnnotations();
          renderBadge();
          renderDrawer();
        });
        item.appendChild(q);
        item.appendChild(del);
        list.appendChild(item);
      }
    }
    drawerEl.appendChild(list);
    const footer = document.createElement("div");
    footer.className = "drawer-footer";
    drawerPushBtn = document.createElement("button");
    drawerPushBtn.className = "drawer-push";
    drawerPushBtn.type = "button";
    drawerPushBtn.textContent = "Pousser sur kenboard";
    drawerPushBtn.disabled = annotations.length === 0;
    drawerPushBtn.addEventListener("click", () => {
      pushToKenboard().catch((err) => setDrawerStatus(`Erreur: ${err?.message ?? err}`, "error"));
    });
    drawerStatusEl = document.createElement("div");
    drawerStatusEl.className = "drawer-status";
    footer.appendChild(drawerPushBtn);
    footer.appendChild(drawerStatusEl);
    drawerEl.appendChild(footer);
  }
  function setDrawerStatus(msg, cls = "") {
    if (!drawerStatusEl) return;
    drawerStatusEl.textContent = msg;
    drawerStatusEl.className = "drawer-status" + (cls ? " " + cls : "");
  }
  async function pushToKenboard() {
    setDrawerStatus("");
    const cfg = await chrome.storage.local.get(["baseUrl", "apiToken", "projectId", "defaultWho"]);
    if (!cfg.baseUrl || !cfg.apiToken || !cfg.projectId) {
      setDrawerStatus("Configurez baseUrl / apiToken / projectId dans les r\xE9glages.", "error");
      return;
    }
    if (annotations.length === 0) return;
    if (drawerPushBtn) drawerPushBtn.disabled = true;
    setDrawerStatus("Envoi\u2026");
    const description = buildMarkdown({
      pageTitle: document.title,
      pageUrl: canonicalUrl(),
      annotations: annotations.map((a) => ({
        quote: String(a.quote?.exact ?? ""),
        textFragmentUrl: textFragmentUrl(a.quote)
      }))
    });
    const title = (document.title || canonicalUrl()).slice(0, 250);
    let resp;
    try {
      resp = await fetch(`${cfg.baseUrl}/api/v1/tasks`, {
        method: "POST",
        // Same as popup.js: strip the session cookie so the auth middleware
        // stays on the bearer path (avoids the same-origin CSRF check).
        credentials: "omit",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${cfg.apiToken}`
        },
        body: JSON.stringify({
          project_id: cfg.projectId,
          title,
          description,
          status: "todo",
          who: cfg.defaultWho || ""
        })
      });
    } catch (err) {
      if (drawerPushBtn) drawerPushBtn.disabled = false;
      setDrawerStatus(`Erreur r\xE9seau: ${err.message}`, "error");
      return;
    }
    if (!resp.ok) {
      const text = await resp.text();
      if (drawerPushBtn) drawerPushBtn.disabled = false;
      setDrawerStatus(`HTTP ${resp.status}: ${text.slice(0, 120)}`, "error");
      return;
    }
    const task = await resp.json();
    setDrawerStatus(`T\xE2che #${task.id} cr\xE9\xE9e. Vider les annotations ?`, "success");
    if (drawerPushBtn?.parentNode) {
      const wrap = drawerPushBtn.parentNode;
      drawerPushBtn.remove();
      const clearBtn = document.createElement("button");
      clearBtn.className = "drawer-push";
      clearBtn.type = "button";
      clearBtn.textContent = "Vider les annotations";
      clearBtn.style.background = "#cf222e";
      clearBtn.addEventListener("click", () => {
        for (const a of annotations) unwrapHighlight(a.id);
        annotations = [];
        saveAnnotations();
        renderBadge();
        renderDrawer();
      });
      wrap.insertBefore(clearBtn, drawerStatusEl);
      const keepBtn = document.createElement("button");
      keepBtn.className = "drawer-push";
      keepBtn.type = "button";
      keepBtn.textContent = "Garder pour it\xE9rer";
      keepBtn.style.background = "#57606a";
      keepBtn.style.marginTop = "6px";
      keepBtn.addEventListener("click", () => {
        setDrawerStatus(`T\xE2che #${task.id} cr\xE9\xE9e.`, "success");
        renderDrawer();
      });
      wrap.insertBefore(keepBtn, drawerStatusEl);
    }
  }
  function activate() {
    if (mode) return;
    ensureHost();
    mode = true;
    loadAnnotations().then(() => {
      reapplyAll();
      renderBadge();
    });
  }
  function deactivate() {
    if (!mode) return;
    mode = false;
    hideAdder();
    closeDrawer();
    badgeEl?.classList.remove("on");
  }
  function onKeyDown(e) {
    if (e.altKey && (e.key === "k" || e.key === "K")) {
      e.preventDefault();
      if (mode) deactivate();
      else activate();
      return;
    }
    if (e.key === "Escape" && mode) {
      if (adderEl?.classList.contains("on")) {
        hideAdder();
      } else if (drawerEl?.classList.contains("open")) {
        closeDrawer();
      } else {
        deactivate();
      }
    }
  }
  function onMaybeUrlChange() {
    const cur = canonicalUrl();
    if (cur === lastUrl) return;
    lastUrl = cur;
    unwrapAllHighlights();
    annotations = [];
    renderBadge();
    if (mode) {
      loadAnnotations().then(() => {
        reapplyAll();
        renderBadge();
        if (drawerEl?.classList.contains("open")) renderDrawer();
      });
    }
  }
  function patchHistory() {
    const orig = history.pushState;
    history.pushState = function(...args) {
      const r = orig.apply(this, args);
      queueMicrotask(onMaybeUrlChange);
      return r;
    };
    const origReplace = history.replaceState;
    history.replaceState = function(...args) {
      const r = origReplace.apply(this, args);
      queueMicrotask(onMaybeUrlChange);
      return r;
    };
    window.addEventListener("popstate", onMaybeUrlChange);
  }
  function bootstrap() {
    lastUrl = canonicalUrl();
    document.addEventListener("keydown", onKeyDown, true);
    document.addEventListener("selectionchange", onSelectionChange);
    patchHistory();
    if (typeof chrome !== "undefined" && chrome.runtime?.onMessage) {
      chrome.runtime.onMessage.addListener((msg) => {
        if (msg?.type === "kb-annotate-start") activate();
      });
    }
  }
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bootstrap, { once: true });
  } else {
    bootstrap();
  }
})();
