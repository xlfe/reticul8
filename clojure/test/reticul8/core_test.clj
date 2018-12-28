(ns reticul8.core-test
  (:require [clojure.test :refer :all]
            [reticul8.protobuf :as pb]
            [reticul8.core :refer :all]))


(def test-bytes (byte-array (map unchecked-byte [24 2 173 1 244 73 4 0 181 1 239 2 0 0 194 12 4 178 182 37 92])))

(deftest a-test
  (testing "FIXME, I fail."
    (is (= {} (pb/from-micro test-bytes)))))
