#ifndef PHLOAT_WEB_H
#define PHLOAT_WEB_H

#include <Arduino.h>

inline String phloat_load_template(const char *tpl) {
  return String(FPSTR(tpl));
}

inline void phloat_tpl_replace(String &html, const char *key, const String &value) {
  html.replace(key, value);
}

#endif
