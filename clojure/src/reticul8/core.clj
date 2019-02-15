(ns reticul8.core
    (:gen-class)
    (:require
      [clojure.core.async :as async]
      [reticul8.protobuf :as pb]
      [protobuf.core :as protobuf]
      [PJON.core :as PJON]))


(def serial-port "/dev/cu.wchusbserial1410")

(defn -main
      []
      (let [incoming (async/chan)
            outgoing (async/chan)]
           (async/<!! (async/go
                        (PJON/transport-loop serial-port incoming outgoing
                                             :ts-byte-time-out-ms 25
                                             :packet-max-length 254)
                        (loop
                          [packet (async/<!! incoming)
                           i 0]
                          (if (contains? packet :data)
                            (let [packet (dissoc (assoc packet :message (dissoc (pb/from-micro (byte-array (:data packet))) :raw)) :data)]
                              (do
                                  (async/put! outgoing {:receiver-id (:sender-id packet) :sender-id 10 :packet-id i :header #{:tx-info} :data (byte-array (protobuf/->bytes (pb/ping i)))})
                                  (if (= 0 (mod i 5))
                                    (println packet))))
                            (println (str "ERROR: " (:error packet))))
                          (recur (async/<!! incoming) (inc i)))))))
