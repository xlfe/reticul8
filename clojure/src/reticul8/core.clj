(ns reticul8.core
    (:gen-class)
    (:require
      [clojure.core.async :as async]
      [reticul8.protobuf :as pb]
      [PJON.core :as PJON]))


(def serial-port "/dev/tty.wchusbserial1410")

(defn -main
      []
      (let [incoming (async/chan)
            outgoing (async/chan)]
           (async/<!! (async/go
                        (PJON/transport-loop serial-port incoming outgoing)
                        (loop
                          [packet (async/<!! incoming)]
                          (println packet)
                          (if (contains? packet :data)
                              (do
                                  (println (pb/from-micro (byte-array (:data packet))))
                                  ;(async/put! outgoing {:receiver-id 11 :sender-id 10 :header #{:ack :tx-info} :data (byte-array [1 2 3 4 5 6 7 8 9 10])})
                                  (recur (async/<!! incoming)))
                              (println (str "ERROR: " (:error packet)))))))))
